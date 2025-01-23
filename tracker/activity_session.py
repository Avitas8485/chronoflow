from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import unique
from typing import Dict, Optional, List
from models.activity import ActivityData, ActivityCategory, ActivityPattern, TimeLog


@dataclass
class ActivityTransition:
    from_activity: 'ActivityData'
    to_activity: 'ActivityData'
    timestamp: datetime
    duration: timedelta
    pattern: ActivityPattern


@dataclass
class ActivityContext:
    last_activities: List[ActivityData] = field(default_factory=list)
    category_durations: Dict[ActivityCategory, float] = field(default_factory=dict)
    activity_patterns: List[ActivityPattern] = field(default_factory=list)
    transition_history: List[ActivityTransition] = field(default_factory=list)
    focus_score: float = 0.0
    
    
    def __post_init__(self):
        self.last_activities = self.last_activities or []
        self.category_durations = self.category_durations or {}
        self.activity_patterns = self.activity_patterns or []
        self.transition_history = self.transition_history or []

class ActivitySession:
    def __init__(self, 
                 min_duration: float = 30.0,  # 30 seconds
                 merge_threshold: float = 300.0,  # 5 minutes
                 context_window: int = 5,
                 min_focus_duration: float = 900.0,  # 15 minutes
                 max_context_transitions: int = 20
                 ):  
        self.min_duration = min_duration
        self.merge_threshold = merge_threshold
        self.context_window = context_window
        self.min_focus_duration = min_focus_duration
        self.max_context_transitions = max_context_transitions
        
        self.current_activity: Optional[ActivityData] = None
        self.activity_start: Optional[datetime] = None
        self.context = ActivityContext()
        self.idle_start: Optional[datetime] = None
        self.pending_activities: List[TimeLog] = []
        self.last_transition: Optional[datetime] = None
        self.pattern_window: deque = deque(maxlen=max_context_transitions)
        
    def update(self, activity: ActivityData) -> Optional[TimeLog]:
        """Update session with new activity data and return a TimeLog if activity should be logged"""
        now = datetime.now()
        
        if self._handle_idle_state(activity, now):
            return self._create_idle_log(now)
        
        current_pattern = self._detect_activity_pattern(activity)
        self.pattern_window.append(current_pattern)
        
        if not self.current_activity:
            self._start_new_activity(activity, now)
            return None
        
        if self._should_transition_activity(activity):
            return self._handle_activity_transition(activity, now)
        
        self._update_context_metrics(activity)
        return None
        
    def _handle_idle_state(self, activity: ActivityData, now: datetime) -> bool:
        if activity.idle_time > 0:
            if not self.idle_start:
                self.idle_start = now
                return False
            
            idle_duration = (now - self.idle_start).total_seconds()
            idle_threshold = 60.0  # 1 minute
            context_multiplier = self._get_context_multiplier()
            adjusted_threshold = idle_threshold * context_multiplier
            
            return idle_duration > adjusted_threshold
        else:
            self.idle_start = None
            return False
        
        
    def _get_context_multiplier(self) -> float:
        if not self.context.last_activities:
            return 1.0
        
        pattern_weights = {
            ActivityPattern.FOCUSED: 1.5,
            ActivityPattern.DISTRACTED: 0.7,
            ActivityPattern.MULTITASKING: 1.0,
            ActivityPattern.TRANSITIONING: 0.8,
        }
        
        recent_patterns = list(self.pattern_window)[-3:]
        if not recent_patterns:
            return 1.0
        
        return sum(pattern_weights.get(p, 1.0) for p in recent_patterns) / len(recent_patterns)
    
    def _detect_activity_pattern(self, activity: ActivityData) -> ActivityPattern:
        if not self.context.last_activities:
            return ActivityPattern.TRANSITIONING
        
        recent_activities = self.context.last_activities
        unique_apps = set(a.application for a in recent_activities)
        avg_duration = self._calculate_average_duration(recent_activities)
        transition_rate = self._calculate_transition_rate()
        
        if activity.idle_time > 0:
            return ActivityPattern.IDLE
        elif len(unique_apps) == 1 and avg_duration > self.min_focus_duration:
            return ActivityPattern.FOCUSED
        elif len(unique_apps) > 3 and transition_rate > 0.5:
            return ActivityPattern.DISTRACTED
        elif 1 < len(unique_apps) <= 3 and transition_rate > 0.3:
            return ActivityPattern.MULTITASKING
        else:
            return ActivityPattern.TRANSITIONING
        
    def _calculate_transition_rate(self) -> float:
        if len(self.context.transition_history) < 2:
            return 0.0
        
        transitions = self.context.transition_history[-10:]
        if not transitions:
            return 0.0
        
        total_time = sum(t.duration.total_seconds() for t in transitions)
        transition_count = len(transitions)
        return transition_count / (total_time / 1e-6)
    
    def _calculate_average_duration(self, activities: List[ActivityData]) -> float:
        if not activities or len(activities) < 2:
            return 0.0
        
        durations = []
        for i in range(len(activities) - 1):
            duration = (activities[i + 1].timestamp - activities[i].timestamp).total_seconds()
            durations.append(duration)
            
        return sum(durations) / len(durations)
    
    def _should_transition_activity(self, new_activity: ActivityData) -> bool:
        if not self.current_activity:
            return True
        
        if new_activity.application != self.current_activity.application:
            return True
        
        title_similarity = self._get_title_similarity(new_activity.window_title, self.current_activity.window_title)
        # Consider context for transition threshold
        base_threshold = 0.7
        context_adjustment = self._get_context_transition_threshold()
        
        return title_similarity < (base_threshold * context_adjustment)
    
    def _get_context_transition_threshold(self) -> float:
        if not self.pattern_window:
            return 1.0
            
        # Adjust threshold based on recent patterns
        pattern_adjustments = {
            ActivityPattern.FOCUSED: 1.2,  # Higher threshold during focus
            ActivityPattern.DISTRACTED: 0.8,  # Lower threshold when distracted
            ActivityPattern.MULTITASKING: 0.9,
            ActivityPattern.TRANSITIONING: 1.0,
            ActivityPattern.IDLE: 1.1
        }
        
        recent_patterns = list(self.pattern_window)[-3:]
        if not recent_patterns:
            return 1.0
            
        return sum(pattern_adjustments.get(p, 1.0) for p in recent_patterns) / len(recent_patterns)
        
            
            
    
    def _is_different_activity(self, new_activity: ActivityData) -> bool:
        if not self.current_activity:
            return True
            
        # Check if applications and titles match
        basic_match = (
            new_activity.application != self.current_activity.application or
            new_activity.window_title != self.current_activity.window_title
        )
        
        # Consider context when determining if activity is different
        if basic_match:
            # Check if similar activities occurred recently
            similar_recent = any(
                self._are_activities_similar(a, new_activity)
                for a in self.context.last_activities[-3:]
            )
            return not similar_recent
            
        return basic_match
    
    def _are_activities_similar(self, a1: ActivityData, a2: ActivityData) -> bool:
        """Compare activities for similarity based on various heuristics"""
        if a1.application == a2.application:
            # For same application, check title similarity
            return self._get_title_similarity(a1.window_title, a2.window_title) > 0.7
        return False
    
    def _get_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity ratio between window titles"""
        import difflib
        sequence_ratio = difflib.SequenceMatcher(None, title1, title2).ratio()
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        if not words1 or not words2:
            word_overlap = 0.0
        else:
            word_overlap = len(words1 & words2) / len(words1 | words2)
        
        # Combine similarities with weights
        return 0.7 * sequence_ratio + 0.3 * word_overlap
    
    def _handle_activity_transition(self, new_activity: ActivityData, now: datetime) -> Optional[TimeLog]:
        """Handle activity transitions with enhanced context awareness"""
        if not self.activity_start:
            self._start_new_activity(new_activity, now)
            return None
            
        duration = (now - self.activity_start).total_seconds()
        
        # Only log if minimum duration met
        if duration >= self.min_duration:
            time_log = self._create_time_log(now)
            
            # Record transition
            if self.current_activity:
                transition = ActivityTransition(
                    from_activity=self.current_activity,
                    to_activity=new_activity,
                    timestamp=now,
                    duration=timedelta(seconds=duration),
                    pattern=self._detect_activity_pattern(new_activity)
                )
                self.context.transition_history.append(transition)
            
            self._start_new_activity(new_activity, now)
            return time_log
            
        # Update current activity
        self._start_new_activity(new_activity, now)
        return None
    
    def _start_new_activity(self, activity: ActivityData, timestamp: datetime):
        self.current_activity = activity
        self.activity_start = timestamp
        
        # Update context
        self.context.last_activities.append(activity)
        if activity.category:
            self.context.category_durations[activity.category] = (
                self.context.category_durations.get(activity.category, 0.0) +
                (timestamp - self.activity_start).total_seconds()
                if self.activity_start else 0.0
            )
            
    def _end_current_activity(self, end_time: datetime) -> Optional[TimeLog]:
        if not self.current_activity or not self.activity_start:
            return None
            
        return TimeLog(
            start_time=self.activity_start,
            end_time=end_time,
            category=self.current_activity.category or ActivityCategory.OTHER,
            description=f"[Auto] {self.current_activity.application}: {self.current_activity.window_title}",
            tags=["auto-tracked"]
        )
        
    def _create_time_log(self, end_time: datetime) -> Optional[TimeLog]:
        """Create enhanced time log with context information"""
        if not self.current_activity or not self.activity_start:
            return None
            
        # Calculate focus score
        focus_score = self._calculate_focus_score()
        
        # Create enhanced description
        description = self._create_enhanced_description(focus_score)
        
        return TimeLog(
            start_time=self.activity_start,
            end_time=end_time,
            category=self.current_activity.category or ActivityCategory.OTHER,
            description=description,
            tags=self._generate_activity_tags(focus_score)
        )
        
    def _calculate_focus_score(self) -> float:
        """Calculate focus score based on activity patterns"""
        if not self.pattern_window:
            return 0.5
            
        pattern_scores = {
            ActivityPattern.FOCUSED: 1.0,
            ActivityPattern.MULTITASKING: 0.7,
            ActivityPattern.TRANSITIONING: 0.5,
            ActivityPattern.DISTRACTED: 0.3,
            ActivityPattern.IDLE: 0.0
        }
        
        recent_patterns = list(self.pattern_window)[-5:]
        return sum(pattern_scores.get(p, 0.5) for p in recent_patterns) / len(recent_patterns)
        
    def _create_enhanced_description(self, focus_score: float) -> str:
        """Create detailed activity description with context"""
        if not self.current_activity:
            return "Unknown activity"
            
        base_desc = f"[Auto] {self.current_activity.application}: {self.current_activity.window_title}"
        pattern = self._detect_activity_pattern(self.current_activity)
        
        return f"{base_desc} | Pattern: {pattern.value} | Focus: {focus_score:.2f}"
       
    def _generate_activity_tags(self, focus_score: float) -> List[str]:
        """Generate context-aware tags for the activity"""
        tags = ["auto-tracked"]
        
        # Add pattern-based tags
        if self.current_activity:
            pattern = self._detect_activity_pattern(self.current_activity)
            tags.append(f"pattern:{pattern.value}")
        
        # Add focus-based tags
        if focus_score >= 0.8:
            tags.append("high-focus")
        elif focus_score <= 0.3:
            tags.append("low-focus")
            
        return tags

    def _create_idle_log(self, end_time: datetime) -> Optional[TimeLog]:
        """Create a TimeLog entry for an idle period"""
        if not self.idle_start:
            return None
            
        # Create idle time log
        time_log = TimeLog(
            start_time=self.idle_start,
            end_time=end_time,
            category=ActivityCategory.IDLE,
            description=f"[Auto] Idle Period | Previous: {self.current_activity.application if self.current_activity else 'None'}",
            tags=["auto-tracked", "idle"]
        )
        
        # Reset idle tracking state
        self.idle_start = None
        
        # Update current activity state
        self.current_activity = None
        self.activity_start = None
        
        return time_log

    def _update_context_metrics(self, activity: ActivityData) -> None:
        """Update activity context metrics including durations, focus and patterns"""
        now = datetime.now()
        
        # Update category durations if category exists
        if activity.category and self.activity_start:
            duration = (now - self.activity_start).total_seconds()
            self.context.category_durations[activity.category] = (
                self.context.category_durations.get(activity.category, 0.0) + duration
            )
        
        # Maintain last activities list with size limit
        self.context.last_activities.append(activity)
        if len(self.context.last_activities) > self.context_window:
            self.context.last_activities.pop(0)
        
        # Update activity patterns
        current_pattern = self._detect_activity_pattern(activity)
        self.context.activity_patterns.append(current_pattern)
        if len(self.context.activity_patterns) > self.max_context_transitions:
            self.context.activity_patterns.pop(0)
        
        # Calculate and update focus score
        self.context.focus_score = self._calculate_focus_score()