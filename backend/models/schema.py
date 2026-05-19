from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.database import Base
from typing import Optional
from pydantic import BaseModel
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    googleId = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)    
    name = Column(String, nullable=True)                              
    
    athleteProfile = Column(String, default="")
    stravaAccessToken = Column(String, nullable=True)
    stravaRefreshToken = Column(String, nullable=True)
    stravaAthleteId = Column(String, nullable=True)
    autoGeneratePlans = Column(Boolean, default=False)
    distanceUnit = Column(String, default="metric")
    intervalsApiKey = Column(String, nullable=True)
    ftp = Column(Float, nullable=True)
    lthr = Column(Float, nullable=True)
    maxHr = Column(Integer, nullable=True)                 # Lactate Threshold Heart Rate
    thresholdPace = Column(String, nullable=True)
    chatModel = Column(String, default="gemini-1.5-flash")
    aRace = Column(String, nullable=True)               # Primary A-Race
    trainingPriorities = Column(String, nullable=True)  # General focus/goals
    baselineLookbackWeeks = Column(Integer, default=12) # How many weeks of data to use for baseline calculations

    # FIXED: Use lambda for dynamic timestamps
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")

# --- MERGED PLANNED WORKOUT CLASS ---
class PlannedWorkout(Base):
    __tablename__ = "planned_workouts"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False) # ADDED from bottom definition
    date = Column(DateTime)
    type = Column(String)
    title = Column(String)
    duration = Column(Integer, nullable=True)
    distance = Column(Float, nullable=True)
    trainingLoad = Column(Float, nullable=True)
    description = Column(String)
    completed = Column(Boolean, default=False)
    
    # Linking to local activity ID is best for relational databases
    activityId = Column(Integer, ForeignKey("activities.id"), unique=True, nullable=True) 
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User")
    activity = relationship("Activity", back_populates="plannedWorkout")

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"))
    weekStartDate = Column(DateTime)
    phase = Column(String)      # e.g., "Base", "Build", "Peak", "Taper"
    focus = Column(String)      # e.g., "Aerobic Endurance & Strength"
    targetTss = Column(Integer) # Gemini's planned training load
    
    user = relationship("User")

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)
    stravaId = Column(String, unique=True, nullable=True)
    type = Column(String)
    startDate = Column(DateTime)
    duration = Column(Integer)
    distance = Column(Float, nullable=True)
    avgHr = Column(Float, nullable=True)
    avgPower = Column(Float, nullable=True)
    trainingLoad = Column(Float, nullable=True)
    name = Column(String)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    lapsSynced = Column(Boolean, default=False, nullable=False)
    
    user = relationship("User", back_populates="activities")
    plannedWorkout = relationship("PlannedWorkout", back_populates="activity", uselist=False)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False) # FIXED: Added userId
    role = Column(String)
    content = Column(String)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User")



class ActivityEffort(Base):
    __tablename__ = "activity_efforts"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"))
    sportType = Column(String)      # "Run", "Ride", "Swim"
    distanceName = Column(String)   # e.g., "5k", "10k", "20m Power"
    timeSeconds = Column(Integer)   # Best time in seconds OR Watts
    stravaActivityId = Column(String) 
    date = Column(DateTime)
    
    user = relationship("User")