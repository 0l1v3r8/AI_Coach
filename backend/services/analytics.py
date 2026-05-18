from datetime import datetime, timedelta
import math
from backend.models import schema
from sqlalchemy.orm import Session

def calculate_biological_baseline(db: Session, user_id: int):
    """Estimates FTP and LTHR from historical Strava data."""
    
    # 1. Estimate FTP (95% of 20-minute peak power)
    # Note: We saved watts in the 'timeSeconds' column for power metrics
    # 1. Estimate FTP (95% of highest ever 20-minute peak power)
    pb_20m = db.query(schema.ActivityEffort).filter(
        schema.ActivityEffort.userId == user_id, 
        schema.ActivityEffort.distanceName == "20m Power"
    ).order_by(schema.ActivityEffort.timeSeconds.desc()).first() # desc() to get the highest wattage
    
    ftp = int(pb_20m.timeSeconds * 0.95) if pb_20m else None

    # 2. Estimate LTHR (Highest Average HR from a hard 20-60 min effort)
    # We look for runs between 20 and 60 minutes with the highest average HR
    hard_efforts = db.query(schema.Activity).filter(
        schema.Activity.userId == user_id,
        schema.Activity.duration >= 1200, # 20 mins
        schema.Activity.duration <= 3600, # 60 mins
        schema.Activity.avgHr != None
    ).order_by(schema.Activity.avgHr.desc()).first()

    lthr = int(hard_efforts.avgHr) if hard_efforts else None

    # Save to user profile
    user = db.query(schema.User).filter(schema.User.id == user_id).first()
    if user:
        if ftp: user.ftp = ftp
        if lthr: user.lthr = lthr
        db.commit()

    return {"ftp": ftp, "lthr": lthr}

def calculate_fitness_fatigue(activities, start_date=None, end_date=None):
    """
    Calculates Fitness (CTL), Fatigue (ATL), and Form (TSB) over time.
    CTL constant = 42 days, ATL constant = 7 days.
    """
    if not activities:
        return []

    # Sort activities chronologically
    activities.sort(key=lambda x: x.startDate)
    
    # Initialize values
    ctl = 0.0
    atl = 0.0
    
    # Create a daily dictionary of TSS
    daily_tss = {}
    for act in activities:
        date_str = act.startDate.strftime("%Y-%m-%d")
        # Ensure we have a training load (TSS), default to estimated if missing
        tss = act.trainingLoad or (act.duration / 60.0) * 1.0  # Very rough estimate if no TSS
        daily_tss[date_str] = daily_tss.get(date_str, 0) + tss

    first_date = activities[0].startDate.date()
    last_date = activities[-1].startDate.date()
    
    results = []
    current_date = first_date
    
    while current_date <= last_date:
        date_str = current_date.strftime("%Y-%m-%d")
        tss_today = daily_tss.get(date_str, 0)
        
        # Exponential moving average formulas
        ctl = (tss_today * (1 - math.exp(-1/42))) + (ctl * math.exp(-1/42))
        atl = (tss_today * (1 - math.exp(-1/7))) + (atl * math.exp(-1/7))
        tsb = ctl - atl # Form is yesterday's Fitness minus yesterday's Fatigue
        
        results.append({
            "date": date_str,
            "tss": tss_today,
            "fitness": round(ctl, 1),
            "fatigue": round(atl, 1),
            "form": round(tsb, 1)
        })
        current_date += timedelta(days=1)
        
    return results

