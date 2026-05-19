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

class UserSettingsUpdate(BaseModel):
    autoGeneratePlans: Optional[bool] = None
    distanceUnit: Optional[str] = None
    intervalsApiKey: Optional[str] = None
    baselineLookbackWeeks: Optional[int] = None
    ftp: Optional[float] = None
    lthr: Optional[float] = None
    maxHr: Optional[int] = None
    chatModel: Optional[str] = None