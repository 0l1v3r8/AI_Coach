import os
import time
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.models import schema

logger = logging.getLogger(__name__)

# --- MULTI-SPORT CONFIGURATION ---
SPORT_BENCHMARKS = {
    "Run": {
        "1k": 1000.0, "5k": 5000.0, "10k": 10000.0,
        "Half Marathon": 21097.5, "Marathon": 42195.0
    },
    "Ride": {
        "10k": 10000.0, "10miles":16000.0, "20k": 20000.0, "20miles": 32000.0, "40k": 40000.0,
        "90k": 90000.0, "180k": 180000.0
    },
    "Swim": {
        "100m": 100.0, "400m": 400.0, "750m": 750.0,
        "1500m": 1500.0, "3.8k": 3800.0
    }
}

CYCLING_POWER_DURATIONS = {
    "5s Power": 5, "1m Power": 60, "5m Power": 300,
    "20m Power": 1200, "60m Power": 3600
}

MINIMUM_PB_DISTANCES_KM = {
    "Run": 1.0, "Ride": 5.0, "Swim": 0.1
}

# --- AUTHENTICATION ---
def refresh_strava_token(user: schema.User, db: Session) -> str:
    url = "https://www.strava.com" + "/oauth/token"
    payload = {
        "client_id": os.getenv("STRAVA_CLIENT_ID"),
        "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
        "grant_type": "refresh_token",
        "refresh_token": user.stravaRefreshToken
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        logger.error(f"Failed to automatically refresh Strava token for user {user.id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strava re-auth failed.")
    data = response.json()
    user.stravaAccessToken = data["access_token"]
    db.commit()
    return user.stravaAccessToken

# --- CORE MATHEMATICAL CALCULATORS ---
def calculate_pb_from_laps(laps: List[Dict], target_meters: float) -> Optional[float]:
    best_time = float('inf')
    n = len(laps)
    for i in range(n):
        current_distance = 0.0
        current_time = 0.0
        for j in range(i, n):
            current_distance += laps[j].get('distance', 0.0)
            current_time += laps[j].get('moving_time', 0.0)
            if current_distance >= target_meters:
                excess_distance = current_distance - target_meters
                lap_dist = laps[j].get('distance', 0.0)
                adjusted_time = current_time - (excess_distance * (laps[j].get('moving_time', 0.0) / lap_dist)) if lap_dist > 0 else current_time
                if adjusted_time < best_time:
                    best_time = adjusted_time
                break 
    return int(best_time) if best_time != float('inf') else None

def calculate_peak_power_from_stream(watts_stream: List[int], duration_seconds: int) -> Optional[int]:
    if len(watts_stream) < duration_seconds:
        return None
    current_sum = sum(watts_stream[:duration_seconds])
    max_sum = current_sum
    for i in range(duration_seconds, len(watts_stream)):
        current_sum = current_sum + watts_stream[i] - watts_stream[i - duration_seconds]
        if current_sum > max_sum:
            max_sum = current_sum
    return int(max_sum / duration_seconds)

# --- DATA EXTRACTION & SAVING ---
def save_activity_effort(db: Session, user_id: int, activity_id: str, sport: str, metric_name: str, value: int, activity_date: datetime):
    """Saves the best internal effort for a specific activity."""
    existing = db.query(schema.ActivityEffort).filter(
        schema.ActivityEffort.userId == user_id,
        schema.ActivityEffort.stravaActivityId == activity_id,
        schema.ActivityEffort.distanceName == metric_name
    ).first()
    
    if not existing:
        new_effort = schema.ActivityEffort(
            userId=user_id, sportType=sport, distanceName=metric_name,
            timeSeconds=value, stravaActivityId=activity_id, date=activity_date
        )
        db.add(new_effort)

def parse_and_save_activity_metrics(db: Session, user_id: int, act: schema.Activity, access_token: str) -> Optional[int]:
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Fast exit for activities that require no stream or lap analysis
    if act.type in ["Strength", "Mobility"]:
        return 200

    # 1. TARGETED STREAM EXTRACTION (Power & HR)
    keys_to_fetch = []
    if act.type == "Ride":
        keys_to_fetch = ["watts", "heartrate"]
    elif act.type in ["Run", "OtherCardio"]:
        keys_to_fetch = ["heartrate"]
        
    if keys_to_fetch:
        keys_str = ",".join(keys_to_fetch)
        streams_url = f"https://www.strava.com/api/v3/activities/{act.stravaId}/streams?keys={keys_str}&series_type=time"
        stream_res = requests.get(streams_url, headers=headers)
        
        if stream_res.status_code == 401: return 401 
            
        if stream_res.status_code == 200:
            streams_data = stream_res.json()
            if isinstance(streams_data, list):
                
                # Extract Power Profile (Cycling Only)
                if act.type == "Ride":
                    watts_data = next((stream["data"] for stream in streams_data if stream.get("type") == "watts"), None)
                    if watts_data:
                        for label, secs in CYCLING_POWER_DURATIONS.items():
                            peak_wattage = calculate_peak_power_from_stream(watts_data, secs)
                            if peak_wattage:
                                save_activity_effort(db, user_id, act.stravaId, act.type, label, peak_wattage, act.startDate)
                
                # Extract HR Profile (Cycling, Running, Other Cardio)
                hr_data = next((stream["data"] for stream in streams_data if stream.get("type") == "heartrate"), None)
                if hr_data:
                    peak_20m_hr = calculate_peak_power_from_stream(hr_data, 1200) # 20 mins
                    if peak_20m_hr:
                        save_activity_effort(db, user_id, act.stravaId, act.type, "Peak 20m HR", peak_20m_hr, act.startDate)
        
        time.sleep(1.0)

    # 2. CLASSIC TIME-FOR-DISTANCE EXTRACTION (Cycling, Running, Swimming)
    if act.type in ["Ride", "Run", "Swim"]:
        targets = SPORT_BENCHMARKS.get(act.type)
        if targets:
            laps_url = f"https://www.strava.com/api/v3/activities/{act.stravaId}/laps"
            laps_res = requests.get(laps_url, headers=headers)
            
            if laps_res.status_code == 401: return 401
                
            if laps_res.status_code == 200:
                laps_data = laps_res.json()
                if isinstance(laps_data, list):
                    for name, target_meters in targets.items():
                        calculated_time = calculate_pb_from_laps(laps_data, target_meters)
                        if calculated_time:
                            save_activity_effort(db, user_id, act.stravaId, act.type, name, calculated_time, act.startDate)
    
    return 200

# --- BACKGROUND WORKER ---
def process_laps_safely_background(user_id: int, db_session_factory):
    db = db_session_factory()
    try:
        user = db.query(schema.User).filter(schema.User.id == user_id).first()
        if not user or not user.stravaAccessToken: return

        unprocessed = db.query(schema.Activity).filter(schema.Activity.userId == user_id, schema.Activity.lapsSynced == False).order_by(schema.Activity.startDate.desc()).all()
        if not unprocessed: return

        access_token = user.stravaAccessToken

        for act in unprocessed:
            status_reply = parse_and_save_activity_metrics(db, user_id, act, access_token)
            if status_reply == 401:
                access_token = refresh_strava_token(user, db)
                parse_and_save_activity_metrics(db, user_id, act, access_token)

            act.lapsSynced = True
            db.commit()
            time.sleep(1.5)
    except Exception as e:
        logger.error(f"Unresolved breakdown: {str(e)}")
    finally:
        db.close()