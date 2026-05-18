from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import schema
from backend.models.pydantic import PBUpdate
from backend.core.dependencies import get_current_user
from backend.services.analytics import calculate_biological_baseline, calculate_fitness_fatigue

# Create a router for all dashboard, chart, calendar, and record data
router = APIRouter(prefix="/api", tags=["metrics"])

@router.get("/dashboard/data")
def get_dashboard_data(db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    activities = db.query(schema.Activity).filter(schema.Activity.userId == user.id).all()
    baseline = calculate_biological_baseline(db, user.id)

    if not activities:
        return {"fitness_data": [], "recent": [], "baseline": baseline}
    
    fitness_chart_data = calculate_fitness_fatigue(activities)
        
    recent = sorted(activities, key=lambda x: x.startDate, reverse=True)[:5]
    recent_list = [{"name": a.name, "type": a.type, "date": a.startDate.strftime("%Y-%m-%d"), "distance": round(a.distance or 0, 1)} for a in recent]

    return {"fitness_data": fitness_chart_data[-30:], "recent": recent_list, "baseline": baseline}

@router.get("/analytics/timeseries")
def get_analytics_timeseries(db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    activities = db.query(schema.Activity).filter(schema.Activity.userId == user.id).all()
    if not activities:
        return {"dates": [], "fitness": [], "fatigue": [], "form": []}
    
    daily_data = calculate_fitness_fatigue(activities)
    recent_data = daily_data[-180:]
    return {
        "dates": [d["date"] for d in recent_data],
        "fitness": [d["fitness"] for d in recent_data],
        "fatigue": [d["fatigue"] for d in recent_data],
        "form": [d["form"] for d in recent_data]
    }

@router.get("/calendar")
def get_calendar_data(db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    activities = db.query(schema.Activity).filter(schema.Activity.userId == user.id).all()
    workouts = db.query(schema.PlannedWorkout).filter(schema.PlannedWorkout.activityId == None).all() 
    
    calendar_events = []
    
    for act in activities:
        duration_mins = (act.duration / 60.0) if act.duration else 0.0
        tss_val = act.trainingLoad if act.trainingLoad is not None else (duration_mins * 1.0)

        calendar_events.append({
            "id": act.id,
            "isHistorical": True,
            "date": act.startDate.strftime("%Y-%m-%d"),
            "title": act.name,
            "type": act.type,
            "distance": round(act.distance or 0, 1),
            "tss": round(tss_val, 1)
        })
        
    for w in workouts:
        calendar_events.append({
            "id": w.id,
            "isHistorical": False,
            "date": w.date.strftime("%Y-%m-%d"),
            "title": w.title,
            "type": w.type,
            "distance": w.distance,
            "tss": round(w.trainingLoad, 1) if w.trainingLoad is not None else None
        })
        
    return {"events": calendar_events}

@router.get("/records")
def get_all_records(db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    """Groups all historical efforts by Sport -> Metric."""
    efforts = db.query(schema.ActivityEffort).filter(schema.ActivityEffort.userId == user.id).all()
    
    results = {}
    for eff in efforts:
        if eff.sportType not in results: results[eff.sportType] = {}
        if eff.distanceName not in results[eff.sportType]: results[eff.sportType][eff.distanceName] = []
        
        results[eff.sportType][eff.distanceName].append({
            "id": eff.id,
            "time": eff.timeSeconds,
            "date": eff.date.strftime("%Y-%m-%d"),
            "activityId": eff.stravaActivityId
        })
    return results

@router.put("/pbs/{pb_id}")
def update_pb(pb_id: int, pb_in: PBUpdate, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    # Note: Using ActivityEffort as per our recent database schema upgrade
    pb = db.query(schema.ActivityEffort).filter(schema.ActivityEffort.id == pb_id, schema.ActivityEffort.userId == user.id).first()
    if not pb: raise HTTPException(status_code=404, detail="Record not found")
    
    pb.timeSeconds = pb_in.timeSeconds
    pb.date = datetime.strptime(pb_in.date, "%Y-%m-%d")
    pb.stravaActivityId = pb_in.activityId
    db.commit()
    return {"success": True}