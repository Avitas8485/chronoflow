from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from models.activity import ActivityCategory, ActivityContext, ActivityHeatmap, ActivityMetrics, Interval, TimeLog
from models.analytics import CategoryDistribution, FocusSession, ProductivityTrend, WorkPatterns

class ActivityStorageError(Exception):
    """Base exception for activity storage errors"""
    pass

class ActivityStorage(ABC):
    """Abstract base class for activity storage implementations"""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize database connection and create necessary tables/collections"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection and cleanup resources"""
        pass

    @abstractmethod
    def add_activity(self, time_log: TimeLog, context: ActivityContext) -> str:
        """
        Store a new activity log
        Returns: ID of the created record
        """
        pass

    @abstractmethod
    def get_activity(self, activity_id: str) -> TimeLog:
        """Retrieve a specific activity log by ID"""
        pass

    @abstractmethod
    def update_activity(self, activity_id: str, time_log: TimeLog) -> None:
        """Update an existing activity log"""
        pass

    @abstractmethod
    def delete_activity(self, activity_id: str) -> None:
        """Delete an activity log"""
        pass

    @abstractmethod
    def get_activities(
        self,
        start_date: datetime,
        end_date: datetime,
        category: Optional[ActivityCategory] = None
    ) -> List[TimeLog]:
        """Retrieve activity logs within a date range and optional category"""
        pass

    @abstractmethod
    def get_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        category: Optional[ActivityCategory] = None
    ) -> ActivityMetrics:
        """Calculate activity metrics for a date range and optional category"""
        pass

    @abstractmethod
    def get_heatmap(
        self,
        start_date: datetime,
        end_date: datetime,
        category: Optional[ActivityCategory] = None
    ) -> ActivityHeatmap:
        """Generate activity heatmap data for a date range and optional category"""
        pass

    @abstractmethod
    def get_flow_states(
        self,
        minimum_duration: timedelta,
        category: Optional[ActivityCategory] = None
    ) -> List[TimeLog]:
        """Retrieve flow state sessions matching the criteria"""
        pass

    @abstractmethod
    def backup(self, backup_path: str) -> None:
        """Create a backup of the activity data"""
        pass

    @abstractmethod
    def restore(self, backup_path: str) -> None:
        """Restore activity data from a backup"""
        pass

    @abstractmethod
    def _store_activity_context(self, activity_id: str, context: ActivityContext) -> None:
        """Store activity context data for a given activity"""
        pass

    @abstractmethod
    def get_activity_context(self, activity_id: str) -> Optional[ActivityContext]:
        """Retrieve activity context data for a given activity"""
        pass
    
    @abstractmethod
    def get_activity_contexts(self, start_date: datetime, end_date: datetime, category: Optional[ActivityCategory] = None) -> List[ActivityContext]:
        """Retrieve activity contexts within a date range and optional category"""
        pass
    
    @abstractmethod
    def get_productivity_trends(self, start_date: datetime, end_date: datetime, interval: Interval) -> List[ProductivityTrend]:
        """Calculate productivity trends for a date range with a specific interval"""
        pass
    
    @abstractmethod
    def get_category_distribution(self, start_date: datetime, end_date: datetime) -> CategoryDistribution:
        """Calculate category distribution metrics for a date range"""
        pass
    
    @abstractmethod
    def get_work_patterns(self, days: int=30) -> WorkPatterns:
        """Calculate work patterns and peak productivity hours"""
        pass
    
    @abstractmethod
    def get_focus_sessions(self, threshold: float=0.6, duration_minutes: int=30) -> List[FocusSession]:
        """Retrieve focus sessions based on the threshold and minimum duration"""
        pass