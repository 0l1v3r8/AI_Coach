import os
import requests
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session, sessionmaker

from backend.database import engine, get_db
from backend.models import schema
from backend.core.dependencies import get_current_user
from backend.services.strava_client import refresh_strava_token, process_laps_safely_background, MINIMUM_PB_DISTANCES_KM

logger = logging.getLogger(__name__)

# Create a router for activity-related endpoints
router = APIRouter(prefix="/api", tags=["activities"])

@router.post("/strava/sync")
def sync_strava_history(background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    if not user.stravaAccessToken:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not connected to Strava")
	
    # We leave this at 30 for your testing, but you can change it back to 365 later
    twelve_months_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    existing_ids = set(id_[0] for id_ in db.query(schema.Activity.stravaId).filter(schema.Activity.userId == user.id).all())
    
    access_token = user.stravaAccessToken
    page = 1
    activities_imported = 0

    while True:
        url = "https://www.strava.com" + f"/api/v3/athlete/activities?after={twelve_months_ago}&page={page}&per_page=200"
        res = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
        
        if res.status_code == 401 and user.stravaRefreshToken:
            access_token = refresh_strava_token(user, db)
            continue  
            
        if res.status_code != 200:
            error_msg = f"Strava rejected the request! Status: {res.status_code}, Body: {res.text}"
            logger.error(error_msg)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_msg)
            
        data = res.json()
        if not data: 
            break
            
        for act in data:
            strava_id = str(act["id"])
            sport_type = act.get("sport_type", act.get("type", "Run"))
            normalized_sport = "Ride" if "Ride" in sport_type else "Run" if "Run" in sport_type else "Swim" if "Swim" in sport_type else sport_type
            
            if strava_id not in existing_ids:
                activity_distance_km = act.get("distance", 0.0) / 1000.0
                min_allowed = MINIMUM_PB_DISTANCES_KM.get(normalized_sport, 0.0)
                should_skip_laps = True if activity_distance_km < min_allowed else False

                new_act = schema.Activity(
                    userId=user.id, stravaId=strava_id, type=normalized_sport,
                    startDate=datetime.fromisoformat(act["start_date_local"].replace("Z", "+00:00")),
                    duration=act.get("moving_time", 0), distance=activity_distance_km,
                    avgHr=act.get("average_heartrate"), avgPower=act.get("average_watts"),
                    trainingLoad=act.get("suffer_score"), name=act.get("name"),
                    lapsSynced=should_skip_laps  
                )
                db.add(new_act)
                existing_ids.add(strava_id)
                activities_imported += 1
                
        db.commit()  
        page += 1

    if activities_imported > 0 or True: 
        session_factory = sessionmaker(bind=engine)
        background_tasks.add_task(process_laps_safely_background, user.id, session_factory)

    return {"success": True, "imported": activities_imported}

@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    activity = db.query(schema.Activity).filter(schema.Activity.id == activity_id, schema.Activity.userId == user.id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    db.delete(activity)
    db.commit()
    return {"success": True}