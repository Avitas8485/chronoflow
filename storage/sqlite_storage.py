from contextlib import contextmanager
import logging
import sqlite3
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import uuid

from models.activity import ActivityCategory, ActivityData, ActivityHeatmap, ActivityMetrics, DailyHeatmap, Interval, TimeLog, ActivityTransition, ActivityContext, ActivityPattern
from models.analytics import ActivityStreak, CategoryDistribution, CategoryMetrics, DailyActivity, FocusSession, HourlyProductivity, ProductivityTrend, WorkPatterns
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
            
            # Create activity context table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_context (
                    activity_id TEXT PRIMARY KEY,
                    focus_score REAL NOT NULL, 
                    activity_pattern TEXT NOT NULL,
                    context_activities TEXT NOT NULL,
                    category_durations TEXT NOT NULL,
                    transition_history TEXT,
                    productivity_score REAL DEFAULT 0.0,
                    FOREIGN KEY (activity_id) REFERENCES activities(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_focus_score ON activity_context(focus_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_pattern ON activity_context(activity_pattern)")
            
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_productivity_score ON activity_context(productivity_score)")
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
            
    def add_activity(self, time_log: TimeLog, context: ActivityContext) -> str:
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
            
        if context:
            self._store_activity_context(activity_id, context)
            
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
            
            base_where = "WHERE start_time >= ? AND end_time <= ?"
            params = [start_date.isoformat(), end_date.isoformat()]
            
            if category:
                base_where += " AND category = ?"
                params.append(category.value)

            # Fix duration calculation using proper time units
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as activity_count,
                    SUM(ROUND((julianday(end_time) - julianday(start_time)) * 24 * 60 * 60)) as total_seconds
                FROM activities
                {base_where}
            """, params)
            result = cursor.fetchone()
            
            # Fix peak hours calculation to consider actual duration within each hour
            cursor.execute(f"""
                WITH hour_activity AS (
                    SELECT 
                        CAST(strftime('%H', start_time) AS INTEGER) as hour,
                        SUM(ROUND((
                            julianday(MIN(end_time, datetime(start_time, '+1 hour', 'start of hour'))) - 
                            julianday(start_time)
                        ) * 24 * 60 * 60)) as duration_seconds
                    FROM activities
                    {base_where}
                    GROUP BY CAST(strftime('%H', start_time) AS INTEGER)
                )
                SELECT hour, duration_seconds
                FROM hour_activity
                ORDER BY duration_seconds DESC
                LIMIT 3
            """, params)
            
            peak_hours = [row['hour'] for row in cursor.fetchall()]
            
            activity_count = result['activity_count']
            total_duration = timedelta(seconds=int(result['total_seconds'] or 0))
            
            # Calculate average duration correctly
            avg_duration = (total_duration / activity_count) if activity_count > 0 else timedelta(0)

            # Get category breakdown
            if category:
                categories_breakdown = {category: total_duration}
            else:
                cursor.execute(f"""
                    SELECT 
                        category,
                        SUM(ROUND((julianday(end_time) - julianday(start_time)) * 24 * 60 * 60)) as category_seconds
                    FROM activities
                    {base_where}
                    GROUP BY category
                """, params)
                
                categories_breakdown = {
                    ActivityCategory(row['category']): timedelta(seconds=int(row['category_seconds']))
                    for row in cursor.fetchall()
                }
            
            return ActivityMetrics(
                total_duration=total_duration,
                activity_count=activity_count,
                average_duration=avg_duration,
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
            
    def _store_activity_context(self, activity_id: str, context: ActivityContext) -> None:
        context_activities = json.dumps([
            {
                "timestamp": a.timestamp.isoformat(),
                "application": a.application,
                "window_title": a.window_title,
                "idle_time": a.idle_time,
                "category": a.category.value if a.category else None
            }
            for a in context.last_activities
        ])
        
        category_durations = json.dumps({
            k.value: v for k, v in context.category_durations.items()
        })
        
        transition_history = json.dumps([
            {
                "from_activity": {
                    "application": t.from_activity.application,
                    "window_title": t.from_activity.window_title,
                    "category": t.from_activity.category.value if t.from_activity.category else None
                },
                "to_activity": {
                    "application": t.to_activity.application,
                    "window_title": t.to_activity.window_title,
                    "category": t.to_activity.category.value if t.to_activity.category else None
                },
                "timestamp": t.timestamp.isoformat(),
                "duration": t.duration.total_seconds(),
                "pattern": t.pattern.value
            }
            for t in context.transition_history
        ])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activity_context 
                (activity_id, focus_score, activity_pattern, context_activities, 
                 category_durations, transition_history, productivity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                activity_id,
                context.focus_score,
                context.activity_patterns[-1].value if context.activity_patterns else ActivityPattern.TRANSITIONING.value,
                context_activities,
                category_durations,
                transition_history,
                context.productivity_score
            ))
            conn.commit()
            
    def get_activity_context(self, activity_id: str) -> Optional[ActivityContext]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT focus_score, activity_pattern, context_activities, "
                "category_durations, transition_history, productivity_score "
                "FROM activity_context WHERE activity_id = ?",
                (activity_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
                
            context_activities = json.loads(row["context_activities"])
            last_activities = [
                ActivityData(
                    timestamp=datetime.fromisoformat(a["timestamp"]),
                    application=a["application"],
                    window_title=a["window_title"],
                    idle_time=a["idle_time"],
                    category=ActivityCategory(a["category"]) if a["category"] else None
                )
                for a in context_activities
            ]
            
            category_durations = {
                ActivityCategory(k): v
                for k, v in json.loads(row["category_durations"]).items()
            }
            
            transition_history = []
            if row["transition_history"]:
                transitions = json.loads(row["transition_history"])
                for t in transitions:
                    from_activity = ActivityData(
                        timestamp=datetime.fromisoformat(t["timestamp"]),
                        application=t["from_activity"]["application"],
                        window_title=t["from_activity"]["window_title"],
                        category=ActivityCategory(t["from_activity"]["category"]) if t["from_activity"]["category"] else None,
                        idle_time=0.0
                    )
                    to_activity = ActivityData(
                        timestamp=datetime.fromisoformat(t["timestamp"]),
                        application=t["to_activity"]["application"],
                        window_title=t["to_activity"]["window_title"],
                        category=ActivityCategory(t["to_activity"]["category"]) if t["to_activity"]["category"] else None,
                        idle_time=0.0
                    )
                    transition_history.append(ActivityTransition(
                        from_activity=from_activity,
                        to_activity=to_activity,
                        timestamp=datetime.fromisoformat(t["timestamp"]),
                        duration=timedelta(seconds=t["duration"]),
                        pattern=ActivityPattern(t["pattern"])
                    ))
                    
            return ActivityContext(
                last_activities=last_activities,
                category_durations=category_durations,
                activity_patterns=[ActivityPattern(row["activity_pattern"])],
                transition_history=transition_history,
                focus_score=row["focus_score"],
                productivity_score=row["productivity_score"]
            )
            
    def get_activity_contexts(
        self,
        start_date: datetime,
        end_date: datetime,
        category: Optional[ActivityCategory] = None
    ) -> List[ActivityContext]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT 
                                a.id,
                                ac.focus_score,
                                ac.activity_pattern,
                                ac.context_activities,
                                ac.category_durations,
                                ac.transition_history,
                                ac.productivity_score
                            FROM activities a
                            JOIN activity_context ac ON a.id = ac.activity_id
                            WHERE a.start_time >= ? AND a.end_time <= ? 
                            """, (start_date.isoformat(), end_date.isoformat()))
                                
            if category:
                cursor.execute(" AND category = ?", (category.value,))
                
            rows = cursor.fetchall()

            contexts = []
            for row in rows:
                context_activities = json.loads(row["context_activities"])
                last_activities = [
                    ActivityData(
                        timestamp=datetime.fromisoformat(a["timestamp"]),
                        application=a["application"],
                        window_title=a["window_title"],
                        idle_time=a["idle_time"],
                        category=ActivityCategory(a["category"]) if a["category"] else None
                    )
                    for a in context_activities
                ]
                
                category_durations = {
                    ActivityCategory(k): v
                    for k, v in json.loads(row["category_durations"]).items()
                }
                
                transition_history = []
                if row["transition_history"]:
                    transitions = json.loads(row["transition_history"])
                    for t in transitions:
                        from_activity = ActivityData(
                            timestamp=datetime.fromisoformat(t["timestamp"]),
                            application=t["from_activity"]["application"],
                            window_title=t["from_activity"]["window_title"],
                            category=ActivityCategory(t["from_activity"]["category"]) if t["from_activity"]["category"] else None,
                            idle_time=0.0
                        )
                        to_activity = ActivityData(
                            timestamp=datetime.fromisoformat(t["timestamp"]),
                            application=t["to_activity"]["application"],
                            window_title=t["to_activity"]["window_title"],
                            category=ActivityCategory(t["to_activity"]["category"]) if t["to_activity"]["category"] else None,
                            idle_time=0.0
                        )
                        transition_history.append(ActivityTransition(
                            from_activity=from_activity,
                            to_activity=to_activity,
                            timestamp=datetime.fromisoformat(t["timestamp"]),
                            duration=timedelta(seconds=t["duration"]),
                            pattern=ActivityPattern(t["pattern"])
                        ))
                        
                contexts.append(ActivityContext(
                    last_activities=last_activities,
                    category_durations=category_durations,
                    activity_patterns=[ActivityPattern(row["activity_pattern"])],
                    transition_history=transition_history,
                    focus_score=row["focus_score"],
                    productivity_score=row["productivity_score"]
                ))
                
            return contexts

    def get_productivity_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        interval: Interval = Interval.DAY  # 'day', 'week', 'month'
    )->List[ProductivityTrend]:
        """Get average productivity scores over time intervals"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            interval_sql = {
                'day': "date(a.start_time)",
                'week': "strftime('%Y-%W', a.start_time)",
                'month': "strftime('%Y-%m', a.start_time)"
            }[interval.value]
            
            cursor.execute(f"""
                SELECT 
                    {interval_sql} as period,
                    AVG(ac.productivity_score) as avg_productivity,
                    AVG(ac.focus_score) as avg_focus
                FROM activities a
                JOIN activity_context ac ON a.id = ac.activity_id
                WHERE a.start_time >= ? AND a.end_time <= ?
                GROUP BY period
                ORDER BY period
            """, (start_date.isoformat(), end_date.isoformat()))
            
            return [
                ProductivityTrend(
                    period=row['period'],
                    avg_productivity=row['avg_productivity'],
                    avg_focus=row['avg_focus']
                )
                for row in cursor.fetchall()
            ]

    def get_category_distribution(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> CategoryDistribution:
        """Get detailed category distribution with productivity metrics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    a.category,
                    COUNT(*) as activity_count,
                    AVG(ac.productivity_score) as avg_productivity,
                    AVG(ac.focus_score) as avg_focus,
                    SUM((julianday(a.end_time) - julianday(a.start_time)) * 24) as total_hours
                FROM activities a
                JOIN activity_context ac ON a.id = ac.activity_id
                WHERE a.start_time >= ? AND a.end_time <= ?
                GROUP BY a.category
            """, (start_date.isoformat(), end_date.isoformat()))
            
            return CategoryDistribution(
                categories={
                    ActivityCategory(row['category']): CategoryMetrics(
                        count=row['activity_count'],
                        avg_productivity=row['avg_productivity'],
                        avg_focus=row['avg_focus'],
                        total_hours=row['total_hours']
                    )
                    for row in cursor.fetchall()
                }
            )

    def get_work_patterns(
        self,
        days: int = 30
    ) -> WorkPatterns:
        """Analyze work patterns and productivity correlations"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    time(start_time) as start_hour,
                    AVG(ac.productivity_score) as avg_productivity,
                    AVG(ac.focus_score) as avg_focus,
                    COUNT(*) as frequency
                FROM activities a
                JOIN activity_context ac ON a.id = ac.activity_id
                WHERE a.start_time >= ? AND a.end_time <= ?
                GROUP BY strftime('%H', start_time)
                ORDER BY avg_productivity DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            return WorkPatterns(
                peak_productivity_hours=[
                    HourlyProductivity(
                        hour=row['start_hour'],
                        productivity=row['avg_productivity'],
                        focus=row['avg_focus'],
                        frequency=row['frequency']
                    )
                    for row in cursor.fetchall()
                ]
            )

    def get_focus_sessions(
        self,
        threshold: float = 0.7,
        duration_minutes: int = 30
    ) -> List[FocusSession]:
        """Identify high-focus periods and their characteristics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    a.id,
                    a.start_time,
                    a.end_time,
                    a.category,
                    ac.focus_score,
                    ac.productivity_score,
                    ac.activity_pattern
                FROM activities a
                JOIN activity_context ac ON a.id = ac.activity_id
                WHERE ac.focus_score >= ?
                AND (julianday(a.end_time) - julianday(a.start_time)) * 24 * 60 >= ?
                ORDER BY ac.focus_score DESC
            """, (threshold, duration_minutes))
            
            return [
                FocusSession(
                    start_time=datetime.fromisoformat(row['start_time']),
                    end_time=datetime.fromisoformat(row['end_time']),
                    category=ActivityCategory(row['category']),
                    focus_score=row['focus_score'],
                    productivity_score=row['productivity_score'],
                    pattern=ActivityPattern(row['activity_pattern'])
                )
                for row in cursor.fetchall()
            ]

    def get_activity_streaks(
        self,
        category: ActivityCategory,
        minimum_daily_hours: float = 1.0
    ) -> List[ActivityStreak]:
        """Track consecutive days of activity in a category"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                WITH daily_hours AS (
                    SELECT 
                        date(start_time) as activity_date,
                        SUM((julianday(end_time) - julianday(start_time)) * 24) as hours
                    FROM activities
                    WHERE category = ?
                    GROUP BY date(start_time)
                    HAVING hours >= ?
                )
                SELECT 
                    activity_date,
                    hours,
                    (julianday(activity_date) - julianday(LAG(activity_date) OVER (ORDER BY activity_date))) as day_diff
                FROM daily_hours
                ORDER BY activity_date
            """, (category.value, minimum_daily_hours))
            
            streaks = []
            current_streak = []
            
            for row in cursor.fetchall():
                if not row['day_diff'] or row['day_diff'] == 1.0:
                    current_streak.append({
                        'date': row['activity_date'],
                        'hours': row['hours']
                    })
                else:
                    if current_streak:
                        streaks.append(current_streak)
                    current_streak = [{
                        'date': row['activity_date'],
                        'hours': row['hours']
                    }]
            
            if current_streak:
                streaks.append(current_streak)
                
            return [
                ActivityStreak(
                    streak_days=[
                        DailyActivity(
                            date=streak_day['date'],
                            hours=streak_day['hours']
                        )
                        for streak_day in streak
                    ]
                )
                for streak in streaks
            ]
