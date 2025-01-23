from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, validator

class ActivityCategory(str, Enum):
    WORK = "work"
    STUDY = "study"
    HOBBY = "hobby"
    RELAX = "relax"
    HEALTH = "health"
    EXERCISE = "exercise"
    SOCIAL = "social"
    IDLE = "idle"  # Add IDLE category
    OTHER = "other"
    
class ActivityPattern(str, Enum):
    FOCUSED = "focused"
    DISTRACTED = "distracted"
    MULTITASKING = "multitasking"
    IDLE = "idle"
    TRANSITIONING = "transitioning"

    

class TimeLog(BaseModel):
    start_time: datetime
    end_time: datetime
    category: ActivityCategory
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    
    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time
    
        
class ActivityMetrics(BaseModel):
    total_duration: timedelta
    activity_count: int
    average_duration: timedelta
    peak_hours: list[int]
    categories_breakdown: Dict[ActivityCategory, timedelta]
    
        
class ActivityData(BaseModel):
    timestamp: datetime
    application: str
    window_title: str
    idle_time: float
    category: Optional[ActivityCategory] = None
    
        
class DailyHeatmap(BaseModel):
    hours: List[float] = Field(..., title="List of 24 data points, one for each hour of the day", min_length=24, max_length=24)
    
    @validator('hours')
    def validate_hours(cls, v):
        if len(v) != 24:
            raise ValueError('Must contain exactly 24 values, one for each hour')
        if not all(x >= 0 for x in v):
            raise ValueError('All duration values must be non-negative')
        return v
    
    
class ActivityHeatmap(BaseModel):
    data: Dict[date, DailyHeatmap] = Field(..., title="Mapping of dates to daily heatmaps")