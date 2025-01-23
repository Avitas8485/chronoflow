from contextlib import contextmanager
import logging
import sqlite3
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import uuid

from models.activity import ActivityCategory, ActivityHeatmap, ActivityMetrics, DailyHeatmap, TimeLog
from storage.storage import ActivityStorage, ActivityStorageError

class SQLiteActivityStorage(ActivityStorage):
    def __init__(self, db_path: str = "activities.db"):
        self.db_path = db_path
        self.initialize()
        
    def initialize(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    tags TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_start_time ON activities(start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON activities(category)")
            conn.commit()
            logging.info(f"Connected to SQLite database at {self.db_path}")
            
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def add_activity(self, time_log: TimeLog) -> str:
        activity_id = str(uuid.uuid4())
        tags_json = json.dumps(time_log.tags) if time_log.tags else None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activities (id, start_time, end_time, category, description, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    time_log.start_time.isoformat(),
                    time_log.end_time.isoformat(),
                    time_log.category.value,
                    time_log.description,
                    tags_json
                )
            )
            conn.commit()
            
        return activity_id
    
    def get_activity(self, activity_id: str) -> TimeLog:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT start_time, end_time, category, description, tags FROM activities WHERE id = ?",
                (activity_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ActivityStorageError(f"Activity {activity_id} not found")
                
            return TimeLog(
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]),
                category=ActivityCategory(row["category"]),
                description=row["description"],
                tags=json.loads(row["tags"]) if row["tags"] else None
            )
            
    def update_activity(self, activity_id: str, time_log: TimeLog) -> None:
        tags_json = json.dumps(time_log.tags) if time_log.tags else None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE activities 
                SET start_time = ?, end_time = ?, category = ?, description = ?, tags = ?
                WHERE id = ?
                """,
                (
                    time_log.start_time.isoformat(),
                    time_log.end_time.isoformat(),
                    time_log.category.value,
                    time_log.description,
                    tags_json,
                    activity_id
                )
            )
            conn.commit()
            
    def delete_activity(self, activity_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
            conn.commit()
            
    def get_activities(
        self,
        start_date: datetime,
        end_date: datetime,
        category: Optional[ActivityCategory] = None
    ) -> List[TimeLog]:
        query = """
            SELECT start_time, end_time, category, description, tags 
            FROM activities 
            WHERE start_time >= ? AND end_time <= ?
        """
        params = [start_date.isoformat(), end_date.isoformat()]
        
        if category:
            query += " AND category = ?"
            params.append(category.value)
            
        query += " ORDER BY start_time ASC"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                TimeLog(
                    start_time=datetime.fromisoformat(row["start_time"]),
                    end_time=datetime.fromisoformat(row["end_time"]),
                    category=ActivityCategory(row["category"]),
                    description=row["description"],
                    tags=json.loads(row["tags"]) if row["tags"] else None
                )
                for row in rows
            ]
            
    def get_metrics(self, start_date: datetime, end_date: datetime, category: Optional[ActivityCategory] = None) -> ActivityMetrics:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Base query parts
            base_where = "WHERE start_time >= ? AND end_time <= ?"
            params = [start_date.isoformat(), end_date.isoformat()]
            
            if category:
                base_where += " AND category = ?"
                params.append(category.value)

            # Get total duration and count
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as activity_count,
                    SUM((julianday(end_time) - julianday(start_time)) * 24 * 60 * 60) as total_seconds
                FROM activities
                {base_where}
            """, params)
            result = cursor.fetchone()
            
            activity_count = result['activity_count']
            total_duration = timedelta(seconds=result['total_seconds'] or 0)
            
            # Calculate average duration
            average_duration = timedelta(seconds=result['total_seconds'] / activity_count) if activity_count > 0 else timedelta(0)
            
            # Find peak hours (hours with most activity)
            cursor.execute(f"""
                WITH RECURSIVE
                hours(hour) AS (
                    SELECT 0 UNION ALL SELECT hour + 1 FROM hours WHERE hour < 23
                ),
                hour_durations AS (
                    SELECT 
                        CAST(strftime('%H', start_time) AS INTEGER) as hour,
                        SUM((julianday(
                            MIN(
                                end_time, 
                                time(start_time, '+1 hour', 'start of hour')
                            )
                        ) - julianday(start_time)) * 24) as duration
                    FROM activities
                    {base_where}
                    GROUP BY CAST(strftime('%H', start_time) AS INTEGER)
                )
                SELECT h.hour
                FROM hours h
                LEFT JOIN hour_durations hd ON h.hour = hd.hour
                ORDER BY COALESCE(hd.duration, 0) DESC
                LIMIT 3
            """, params)
            peak_hours = [row['hour'] for row in cursor.fetchall()]
            
            # Get category breakdown
            if category:
                categories_breakdown = {
                    category: total_duration
                }
            else:
                cursor.execute(f"""
                    SELECT 
                        category,
                        SUM((julianday(end_time) - julianday(start_time)) * 24 * 60 * 60) as category_seconds
                    FROM activities
                    {base_where}
                    GROUP BY category
                """, params)
                
                categories_breakdown = {
                    ActivityCategory(row['category']): timedelta(seconds=row['category_seconds'])
                    for row in cursor.fetchall()
                }
            
            return ActivityMetrics(
                total_duration=total_duration,
                activity_count=activity_count,
                average_duration=average_duration,
                peak_hours=peak_hours,
                categories_breakdown=categories_breakdown
            )
            
    def get_heatmap(
        self,
        start_date: datetime,
        end_date: datetime,
        category: Optional[ActivityCategory] = None
    ) -> ActivityHeatmap:
        activities = self.get_activities(start_date, end_date, category)
    
        heatmap: Dict[date, DailyHeatmap] = {}
        current_date = start_date.date()
    
        while current_date <= end_date.date():
            hourly_durations = [0.0] * 24

            for activity in activities:
                if (activity.end_time.date() < current_date or 
                    activity.start_time.date() > current_date):
                    continue
                
                day_start = max(
                    activity.start_time,
                    datetime.combine(current_date, datetime.min.time())
                )
                day_end = min(
                    activity.end_time,
                    datetime.combine(current_date + timedelta(days=1), datetime.min.time())
                )

                start_hour = day_start.hour
                start_minute = day_start.minute
                end_hour = day_end.hour
                end_minute = day_end.minute if day_end.date() == current_date else 0

                if start_hour == end_hour:
                    duration = (day_end - day_start).total_seconds() / 3600
                    hourly_durations[start_hour] += duration
                else:
                    first_hour_duration = (60 - start_minute) / 60
                    if first_hour_duration > 0:
                        hourly_durations[start_hour] += first_hour_duration
                
                    for hour in range(start_hour + 1, end_hour):
                        hourly_durations[hour] += 1.0
                
                    if end_hour < 24:
                        last_hour_duration = end_minute / 60
                        hourly_durations[end_hour] += last_hour_duration
        
            heatmap[current_date] = DailyHeatmap(hours=hourly_durations)
            current_date = current_date + timedelta(days=1)
        
        return ActivityHeatmap(data=heatmap)
    
    def get_flow_states(
        self,
        minimum_duration: timedelta,
        category: Optional[ActivityCategory] = None
    ) -> List[TimeLog]:
        query = """
            SELECT start_time, end_time, category, description, tags 
            FROM activities 
            WHERE (julianday(end_time) - julianday(start_time)) * 24 * 60 * 60 >= ?
        """
        params: List[Union[float, str]] = [minimum_duration.total_seconds()]
        
        if category:
            query += " AND category = ?"
            params.append(category.value)
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                TimeLog(
                    start_time=datetime.fromisoformat(row["start_time"]),
                    end_time=datetime.fromisoformat(row["end_time"]),
                    category=ActivityCategory(row["category"]),
                    description=row["description"],
                    tags=json.loads(row["tags"]) if row["tags"] else None
                )
                for row in rows
            ]
            
    def backup(self, backup_path: str) -> None:
        shutil.copy2(self.db_path, backup_path)
        
    def restore(self, backup_path: str) -> None:
        if not Path(backup_path).exists():
            raise ActivityStorageError(f"Backup file {backup_path} does not exist")
            
        shutil.copy2(backup_path, self.db_path)
        
    def close(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.close()
