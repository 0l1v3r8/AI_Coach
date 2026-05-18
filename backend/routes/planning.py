import json
import base64
import logging
import requests
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import schema
from backend.models.pydantic import MacroPlanRequest, MicroPlanRequest, WorkoutCreate, WorkoutUpdate
from backend.core.dependencies import get_current_user
from backend.services.analytics import calculate_biological_baseline, calculate_fitness_fatigue
from backend.services import gemini_service

logger = logging.getLogger(__name__)

# Create a router for AI planning and workout scheduling endpoints
router = APIRouter(prefix="/api", tags=["planning"])

def clean_gemini_json(raw_text: str) -> str:
    """Strips markdown code blocks from Gemini's response so json.loads doesn't crash."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

@router.post("/plan/macro")
def generate_macro_plan(req: MacroPlanRequest, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    if not user.aRace:
        raise HTTPException(status_code=400, detail="Please set and SAVE an A-Race in your Goals first.")

    start_dt = datetime.strptime(req.startDate, "%Y-%m-%d")
    target_dt = datetime.strptime(req.targetDate, "%Y-%m-%d")
    weeks_to_race = max(1, (target_dt - start_dt).days // 7)

    baseline = calculate_biological_baseline(db, user.id)
    activities = db.query(schema.Activity).filter(schema.Activity.userId == user.id).all()
    chart_data = calculate_fitness_fatigue(activities)
    
    athlete_context = {
        "ftp": baseline["ftp"],
        "lthr": baseline["lthr"],
        "fitness": chart_data[-1]["fitness"] if chart_data else 0.0,
        "fatigue": chart_data[-1]["fatigue"] if chart_data else 0.0
    }

    try:
        raw_json = gemini_service.generate_macro_plan(
            athlete_profile=user.athleteProfile,
            a_race=user.aRace,
            priorities=user.trainingPriorities,
            athlete_context=athlete_context,
            weeks_to_race=weeks_to_race
        )
        
        clean_json_str = clean_gemini_json(raw_json)
        plan_data = json.loads(clean_json_str)
        
        db.query(schema.WeeklyPlan).filter(schema.WeeklyPlan.userId == user.id).delete()
        
        for week in plan_data["plan"]:
            week_date = start_dt + timedelta(weeks=week["week_number"] - 1)
            new_week = schema.WeeklyPlan(
                userId=user.id,
                weekStartDate=week_date,
                phase=week["phase"],
                focus=week["focus"],
                targetTss=week["target_tss"]
            )
            db.add(new_week)
        
        db.commit()
        return {"success": True, "weeks_generated": len(plan_data["plan"])}
        
    except Exception as e:
        logger.error(f"Gemini Macro Plan Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Generation Failed: {str(e)}")

@router.post("/plan/micro")
def generate_micro_plan(req: MicroPlanRequest, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    week_start = datetime.strptime(req.weekStartDate, "%Y-%m-%d")
    
    macro_week = db.query(schema.WeeklyPlan).filter(
        schema.WeeklyPlan.userId == user.id,
        schema.WeeklyPlan.weekStartDate == week_start
    ).first()
    
    focus = macro_week.focus if macro_week else "Base aerobic maintenance"
    target_tss = macro_week.targetTss if macro_week else 300

    baseline = calculate_biological_baseline(db, user.id)
    activities = db.query(schema.Activity).filter(schema.Activity.userId == user.id).all()
    chart_data = calculate_fitness_fatigue(activities)
    current_ctl = chart_data[-1]["fitness"] if chart_data else 0.0
    current_atl = chart_data[-1]["fatigue"] if chart_data else 0.0

    athlete_context = {
        "ftp": baseline["ftp"],
        "lthr": baseline["lthr"],
        "fitness": current_ctl,
        "fatigue": current_atl
    }

    week_dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    try:
        raw_json = gemini_service.generate_micro_plan(athlete_context, focus, target_tss, week_dates)
        
        clean_json_str = clean_gemini_json(raw_json)
        micro_data = json.loads(clean_json_str)

        auth_headers = None
        if user.intervalsApiKey:
            b64_auth = base64.b64encode(f"API_KEY:{user.intervalsApiKey}".encode()).decode()
            auth_headers = {"Authorization": f"Basic {b64_auth}"}

        for wo in micro_data["workouts"]:
            existing = db.query(schema.PlannedWorkout).filter(
                schema.PlannedWorkout.userId == user.id,
                schema.PlannedWorkout.date == datetime.strptime(wo["date"], "%Y-%m-%d")
            ).first()
            
            if not existing:
                new_wo = schema.PlannedWorkout(
                    userId=user.id,
                    date=datetime.strptime(wo["date"], "%Y-%m-%d"),
                    type=wo["type"],
                    title=wo["title"],
                    duration=wo["duration"],
                    trainingLoad=wo["trainingLoad"],
                    description=wo["description"]
                )
                db.add(new_wo)

                if auth_headers:
                    try:
                        payload = {
                            "category": "WORKOUT",
                            "start_date_local": f"{wo['date']}T00:00:00",
                            "type": wo["type"],
                            "name": wo["title"],
                            "description": wo["description"]
                        }
                        res = requests.post("[https://intervals.icu/api/v1/athlete/0/events](https://intervals.icu/api/v1/athlete/0/events)", json=payload, headers=auth_headers)
                    except Exception as e:
                        logger.error(f"Intervals push error: {e}")

        db.commit()
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Gemini Micro Plan Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Generation Failed: {str(e)}")

@router.get("/plan/macro")
def get_macro_plan(db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    """Fetches the user's generated macro plan."""
    plan = db.query(schema.WeeklyPlan).filter(schema.WeeklyPlan.userId == user.id).order_by(schema.WeeklyPlan.weekStartDate.asc()).all()
    return {
        "plan": [{
            "id": w.id,
            "weekStartDate": w.weekStartDate.strftime("%Y-%m-%d"),
            "phase": w.phase,
            "focus": w.focus,
            "targetTss": w.targetTss
        } for w in plan]
    }

@router.post("/workouts")
def schedule_workout(workout: WorkoutCreate, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    new_workout = schema.PlannedWorkout(
        userId=user.id,
        date=datetime.strptime(workout.date, "%Y-%m-%d"),
        type=workout.type,
        title=workout.title,
        duration=workout.duration,
        distance=workout.distance,
        trainingLoad=workout.trainingLoad,
        description=workout.description
    )
    db.add(new_workout)
    db.commit()

    if user.intervalsApiKey:
        try:
            auth_string = f"API_KEY:{user.intervalsApiKey}"
            b64_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {"Authorization": f"Basic {b64_auth}"}
            
            payload = {
                "category": "WORKOUT",
                "start_date_local": f"{workout.date}T00:00:00",
                "type": workout.type,
                "name": workout.title,
                "description": workout.description
            }
            res = requests.post("[https://intervals.icu/api/v1/athlete/0/events](https://intervals.icu/api/v1/athlete/0/events)", json=payload, headers=headers)
            if res.status_code != 200:
                logger.error(f"Failed to push to intervals: {res.text}")
        except Exception as e:
            logger.error(f"Intervals push error: {e}")

    return {"success": True}

@router.put("/workouts/{workout_id}")
def update_workout(workout_id: int, workout: WorkoutUpdate, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    """Allows the user to manually edit a planned workout."""
    wo = db.query(schema.PlannedWorkout).filter(schema.PlannedWorkout.id == workout_id, schema.PlannedWorkout.userId == user.id).first()
    if not wo: raise HTTPException(status_code=404, detail="Workout not found")
    
    wo.title = workout.title
    wo.type = workout.type
    wo.duration = workout.duration
    wo.trainingLoad = workout.trainingLoad
    wo.description = workout.description
    db.commit()
    return {"success": True}

@router.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    """Deletes a planned workout."""
    wo = db.query(schema.PlannedWorkout).filter(schema.PlannedWorkout.id == workout_id, schema.PlannedWorkout.userId == user.id).first()
    if not wo: raise HTTPException(status_code=404, detail="Workout not found")
    db.delete(wo)
    db.commit()
    return {"success": True}