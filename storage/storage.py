from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from models.activity import ActivityCategory, ActivityHeatmap, ActivityMetrics, TimeLog

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
    def add_activity(self, time_log: TimeLog) -> str:
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