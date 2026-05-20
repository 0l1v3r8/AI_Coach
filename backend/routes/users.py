from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import schema
from backend.models.pydantic import GoalUpdate
from backend.core.dependencies import get_current_user
from backend.models.pydantic import UserSettingsUpdate

# Create a router specifically for all /api/users endpoints
router = APIRouter(prefix="/api/users", tags=["users"])



@router.put("/settings")
def update_user_settings(settings: UserSettingsUpdate, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    # Update only the fields that were provided in the request
    update_data = settings.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(user, key, value)
        
    db.commit()
    return {"success": True, "message": "Settings updated successfully"}

@router.get("/me")
def read_current_user(user: schema.User = Depends(get_current_user)):
    return {
        "name": user.name, 
        "email": user.email, 
        "profile": user.athleteProfile,
        "aRace": user.aRace,
        "trainingPriorities": user.trainingPriorities,
        "stravaConnected": user.stravaAccessToken is not None,
        "intervalsConnected": user.intervalsApiKey is not None,
        "baselineLookbackWeeks": user.baselineLookbackWeeks # <-- Add this line
    }

@router.post("/strava/disconnect")
def disconnect_strava(db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    user.stravaAccessToken = None
    user.stravaRefreshToken = None
    user.stravaAthleteId = None
    db.commit()
    return {"success": True}

@router.post("/intervals/disconnect")
def disconnect_intervals(db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    user.intervalsApiKey = None
    db.commit()
    return {"success": True}

@router.put("/goals")
def update_goals(goals: GoalUpdate, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    user.aRace = goals.aRace
    user.trainingPriorities = goals.trainingPriorities
    db.commit()
    return {"success": True}