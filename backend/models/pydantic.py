from pydantic import BaseModel
from typing import Optional

class WorkoutCreate(BaseModel):
    date: str
    type: str
    title: str
    duration: Optional[int] = None
    distance: Optional[float] = None
    trainingLoad: Optional[float] = None
    description: str

class WorkoutUpdate(BaseModel):
    title: str
    type: str
    duration: Optional[int] = None
    trainingLoad: Optional[float] = None
    description: str

class GoalUpdate(BaseModel):
    aRace: Optional[str] = None
    trainingPriorities: Optional[str] = None

class PBUpdate(BaseModel):
    timeSeconds: int
    date: str
    activityId: Optional[str] = None

class MacroPlanRequest(BaseModel):
    startDate: str # YYYY-MM-DD
    targetDate: str # YYYY-MM-DD

class MicroPlanRequest(BaseModel):
    weekStartDate: str # YYYY-MM-DD

class WeeklyPlanUpdate(BaseModel):
    phase: str
    focus: str
    targetTss: int