from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
from models.activity import ActivityCategory
from models.rules import ActivityPattern, CategoryRule, DefaultRule, RulesMetadata, ActivityRules
import logging
import json
from pathlib import Path
from difflib import SequenceMatcher
import re


class ActivityClassifier:
    def __init__(self, rules_file: Optional[Path]=Path('activity_rules.json')):
        self.rules_file = rules_file or Path('activity_rules.json')
        self.rules: ActivityRules = self._load_rules(rules_file)
        
    def _load_rules(self, rules_file: Optional[Path]) -> ActivityRules:
        if (rules_file and rules_file.exists()):
            with open(rules_file, 'r') as f:
                data = json.load(f)
                return ActivityRules.parse_obj(data)
        
        # Default rules
        return ActivityRules(
            rules={
                ActivityCategory.WORK: CategoryRule(
                    priority=1,
                    patterns=[
                        ActivityPattern(
                            apps=["code.exe", "visual studio code"],
                            titles=["*.py", "*.java"],
                            time_ranges=["09:00-17:00"],
                            days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                        )
                    ]
                )
                # ... other categories
            },
            default=DefaultRule(
                category=ActivityCategory.OTHER,
                priority=100
            ),
            metadata=RulesMetadata(
                version="1.0",
                last_updated=datetime.now()
            )
        )

    def classify_activity(self, app_name: str, window_title: str, timestamp: Optional[datetime], idle_time: float = 0.0) -> Tuple[Optional[ActivityCategory], float]:
        # Check for idle state first
        if idle_time >= 300.0:  # 5 minutes default idle threshold
            return ActivityCategory.IDLE, 1.0
            
        if self._should_exclude_activity(app_name, window_title):
            return None, 0.0
            
        if timestamp is None:
            timestamp = datetime.now()

        current_time = timestamp.strftime("%H:%M")
        current_day = timestamp.strftime("%A")

        best_match = None
        highest_score = 0.0
        highest_priority = float('inf')

        for category, rule_set in self.rules.rules.items():
            if rule_set.priority >= highest_priority:
                continue
            
            for pattern in rule_set.patterns:
                # Calculate pattern match scores
                app_score = max(self._calculate_pattern_score(app_name.lower(), app.lower()) 
                              for app in pattern.apps)
                
                title_score = max(self._calculate_pattern_score(window_title.lower(), title.lower()) 
                                for title in pattern.titles)

                # Time and day scoring
                time_score = 1.0
                if pattern.time_ranges:
                    time_scores = [self._calculate_time_score(current_time, time_range) 
                                 for time_range in pattern.time_ranges]
                    time_score = max(time_scores)

                day_score = 1.0
                if pattern.days:
                    day_score = 1.0 if current_day in pattern.days else 0.2

                # Calculate weighted total score
                total_score = (app_score * 0.4 + 
                             title_score * 0.4 + 
                             time_score * 0.1 + 
                             day_score * 0.1)

                if total_score > highest_score:
                    highest_score = total_score
                    best_match = category
                    highest_priority = rule_set.priority

        if not best_match or highest_score < 0.3:
            return self.rules.default.category, 0.3
            
        return best_match, highest_score

    def _calculate_pattern_score(self, text: str, pattern: str) -> float:
        # Exact match
        if pattern == text:
            return 1.0
            
        # Wildcard pattern matching
        if '*' in pattern:
            if self._match_pattern(text, pattern):
                return 0.9
                
        # Fuzzy string matching
        return SequenceMatcher(None, text, pattern).ratio()

    def _calculate_time_score(self, current_time: str, time_range: str) -> float:
        start, end = time_range.split('-')
        if self._is_time_in_range(current_time, time_range):
            return 1.0
            
        # Calculate proximity to time range
        current_mins = self._time_to_minutes(current_time)
        start_mins = self._time_to_minutes(start)
        end_mins = self._time_to_minutes(end)
        
        min_distance = min(
            abs(current_mins - start_mins),
            abs(current_mins - end_mins)
        )
        
        # Score decreases with distance from time range
        return max(0, 1 - (min_distance / 180))  # 3 hour max distance

    def _time_to_minutes(self, time_str: str) -> int:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes

    def _should_exclude_activity(self, app_name: str, window_title: str) -> bool:
        """Check if activity should be excluded based on privacy rules"""
        app_name = app_name.lower()
        window_title = window_title.lower()
        
        # Check excluded apps
        if any(self._match_pattern(app_name, excluded) 
              for excluded in self.rules.privacy.excluded_apps):
            return True
            
        # Check excluded titles
        if any(self._match_pattern(window_title, excluded) 
              for excluded in self.rules.privacy.excluded_titles):
            return True
            
        return False

    def _match_pattern(self, text: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(text, pattern.lower())

    def _is_time_in_range(self, current_time: str, time_range: str) -> bool:
        start, end = time_range.split('-')
        return start <= current_time <= end

    def add_rule(self, category: ActivityCategory, pattern: ActivityPattern, priority: Optional[int] = None) -> None:
        if category not in self.rules.rules:
            self.rules.rules[category] = CategoryRule(priority=priority or 50, patterns=[])
        
        self.rules.rules[category].patterns.append(pattern)
        self._save_rules()

    def update_category_priority(self, category: ActivityCategory, priority: int) -> None:
        if category not in self.rules.rules:
            raise ValueError(f"Category {category} not found")
        
        self.rules.rules[category].priority = priority
        self._save_rules()
        
    
        
    def _save_rules(self) -> None:
        """Save rules to JSON file with proper datetime handling"""
        try:
            self.rules.metadata.last_updated = datetime.now()
            
            # Convert model to dict with custom datetime handling
            rules_dict = self.rules.model_dump()
            rules_dict['metadata']['last_updated'] = self.rules.metadata.last_updated.isoformat()
            
            with open(self.rules_file, 'w') as f:
                json.dump(rules_dict, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving rules: {e}")
            raise
        
    def remove_pattern(self, category: ActivityCategory, pattern_id: str) -> None:
        if category not in self.rules.rules:
            raise ValueError(f"Category {category} not found")
        
        patterns = self.rules.rules[category].patterns
        for i, pattern in enumerate(patterns):
            if pattern.id == pattern_id:
                patterns.pop(i)
                self._save_rules()
                return
                
        raise ValueError(f"Pattern {pattern_id} not found")

    def remove_category(self, category: ActivityCategory) -> None:
        if category not in self.rules.rules:
            raise ValueError(f"Category {category} not found")
        
        del self.rules.rules[category]
        self._save_rules()

    def add_privacy_rule(self, excluded_app: Optional[str] = None, excluded_title: Optional[str] = None) -> None:
        """Add new privacy exclusion rule"""
        if excluded_app:
            self.rules.privacy.excluded_apps.append(excluded_app)
        if excluded_title:
            self.rules.privacy.excluded_titles.append(excluded_title)
        self._save_rules()

    def modify_pattern(self, 
                      category: ActivityCategory,
                      pattern_id: str,
                      apps: Optional[List[str]] = None,
                      titles: Optional[List[str]] = None,
                      time_ranges: Optional[List[str]] = None,
                      days: Optional[List[str]] = None) -> None:
        """
        Modify an existing pattern within a category rule.
        Only provided parameters will be updated.
        """
        if category not in self.rules.rules:
            raise ValueError(f"Category {category} not found")
            
        for pattern in self.rules.rules[category].patterns:
            if pattern.id == pattern_id:
                if apps is not None:
                    pattern.apps = apps
                if titles is not None:
                    pattern.titles = titles
                if time_ranges is not None:
                    pattern.time_ranges = time_ranges
                if days is not None:
                    pattern.days = days
                self._save_rules()
                return
                
        raise ValueError(f"Pattern {pattern_id} not found")

    def modify_privacy_rule(self,
                           old_app: Optional[str] = None,
                           new_app: Optional[str] = None,
                           old_title: Optional[str] = None, 
                           new_title: Optional[str] = None) -> None:
        """
        Modify existing privacy rules by matching patterns.
        
        Args:
            old_app: Existing app pattern to modify
            new_app: New app pattern to set
            old_title: Existing title pattern to modify
            new_title: New title pattern to set
        """
        if old_app is not None and new_app is not None:
            try:
                idx = self.rules.privacy.excluded_apps.index(old_app)
                self.rules.privacy.excluded_apps[idx] = new_app
            except ValueError:
                raise ValueError(f"App pattern '{old_app}' not found in privacy rules")
                
        if old_title is not None and new_title is not None:
            try:
                idx = self.rules.privacy.excluded_titles.index(old_title)
                self.rules.privacy.excluded_titles[idx] = new_title
            except ValueError:
                raise ValueError(f"Title pattern '{old_title}' not found in privacy rules")
                
        self._save_rules()
