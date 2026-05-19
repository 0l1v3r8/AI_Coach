from datetime import datetime, timedelta
import math
from backend.models import schema
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone # Ensure timedelta and timezone are imported
from backend.models import schema
from sqlalchemy.orm import Session

def calculate_biological_baseline(db: Session, user_id: int):
    """Estimates FTP, LTHR, and Max HR from high-fidelity stream data within a configurable timeframe."""
    
    user = db.query(schema.User).filter(schema.User.id == user_id).first()
    if not user:
        return {"ftp": None, "lthr": None, "maxHr": None}
        
    # Calculate the cutoff date based on user settings (default to 12 weeks if not set)
    lookback_weeks = user.baselineLookbackWeeks if user.baselineLookbackWeeks is not None else 12
    cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=lookback_weeks)
    
    # 1. Estimate FTP (95% of highest 20-minute peak power within timeframe)
    pb_20m = db.query(schema.ActivityEffort).filter(
        schema.ActivityEffort.userId == user_id, 
        schema.ActivityEffort.distanceName == "20m Power",
        schema.ActivityEffort.date >= cutoff_date  # <-- NEW FILTER
    ).order_by(schema.ActivityEffort.timeSeconds.desc()).first()
    
    ftp = int(pb_20m.timeSeconds * 0.95) if pb_20m else None

    # 2. Estimate LTHR (Using the precise Peak 20m HR extracted from streams)
    peak_20m_hr_effort = db.query(schema.ActivityEffort).filter(
        schema.ActivityEffort.userId == user_id,
        schema.ActivityEffort.distanceName == "Peak 20m HR",
        schema.ActivityEffort.date >= cutoff_date  # <-- NEW FILTER
    ).order_by(schema.ActivityEffort.timeSeconds.desc()).first()
    
    lthr = int(peak_20m_hr_effort.timeSeconds) if peak_20m_hr_effort else None

    # 3. Estimate Max HR (Using the highest 15-second HR burst)
    max_hr_effort = db.query(schema.ActivityEffort).filter(
        schema.ActivityEffort.userId == user_id,
        schema.ActivityEffort.distanceName == "Max HR",
        schema.ActivityEffort.date >= cutoff_date  # <-- NEW FILTER
    ).order_by(schema.ActivityEffort.timeSeconds.desc()).first()
    
    max_hr = int(max_hr_effort.timeSeconds) if max_hr_effort else None

    # Save to user profile
    if ftp: user.ftp = ftp
    if lthr: user.lthr = lthr
    if max_hr: user.maxHr = max_hr
    db.commit()

    return {"ftp": ftp, "lthr": lthr, "maxHr": max_hr}

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

