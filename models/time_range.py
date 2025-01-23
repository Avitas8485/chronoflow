from enum import Enum
from datetime import datetime, timedelta

class TimeRange(Enum):
    TODAY = "Today"
    WEEK = "This Week"
    MONTH = "This Month"
    QUARTER = "This Quarter"
    YEAR = "This Year"
    
    def get_date_range(self) -> tuple[datetime, datetime]:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        match self:
            case TimeRange.TODAY:
                return today_start, today_start + timedelta(days=1)
            case TimeRange.WEEK:
                week_start = today_start - timedelta(days=now.weekday())
                return week_start, week_start + timedelta(days=7)
            case TimeRange.MONTH:
                month_start = today_start.replace(day=1)
                if now.month == 12:
                    next_month = month_start.replace(year=now.year + 1, month=1)
                else:
                    next_month = month_start.replace(month=now.month + 1)
                return month_start, next_month
            case TimeRange.QUARTER:
                quarter = (now.month - 1) // 3
                quarter_start = today_start.replace(month=quarter * 3 + 1, day=1)
                if quarter == 3:
                    next_quarter = quarter_start.replace(year=now.year + 1, month=1)
                else:
                    next_quarter = quarter_start.replace(month=quarter_start.month + 3)
                return quarter_start, next_quarter
            case TimeRange.YEAR:
                year_start = today_start.replace(month=1, day=1)
                next_year = year_start.replace(year=now.year + 1)
                return year_start, next_year