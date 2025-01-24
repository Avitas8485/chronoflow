from datetime import datetime
from typing import Dict, List
from pydantic import BaseModel
from .activity import ActivityCategory, ActivityPattern

class ProductivityTrend(BaseModel):
    period: str  # ISO formatted date/time period
    avg_productivity: float
    avg_focus: float

class CategoryMetrics(BaseModel):
    count: int
    avg_productivity: float
    avg_focus: float
    total_hours: float

class CategoryDistribution(BaseModel):
    categories: Dict[ActivityCategory, CategoryMetrics]

class HourlyProductivity(BaseModel):
    hour: str  # Time in HH:MM format
    productivity: float
    focus: float
    frequency: int

class WorkPatterns(BaseModel):
    peak_productivity_hours: List[HourlyProductivity]

class FocusSession(BaseModel):
    start_time: datetime
    end_time: datetime
    category: ActivityCategory
    focus_score: float
    productivity_score: float
    pattern: ActivityPattern

class DailyActivity(BaseModel):
    date: datetime
    hours: float

class ActivityStreak(BaseModel):
    streak_days: List[DailyActivity]