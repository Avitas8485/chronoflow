from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from models.activity import ActivityCategory
from uuid import uuid4

class ActivityPattern(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    apps: List[str]
    titles: List[str] 
    time_ranges: Optional[List[str]] = None
    days: Optional[List[str]] = None

class CategoryRule(BaseModel):
    priority: int = Field(ge=1, le=100)
    patterns: List[ActivityPattern]

class DefaultRule(BaseModel):
    category: ActivityCategory
    priority: int = Field(default=100, ge=1, le=100)

class RulesMetadata(BaseModel):
    version: str
    last_updated: datetime

class PrivacyRule(BaseModel):
    excluded_apps: List[str] = Field(default_factory=list)
    excluded_titles: List[str] = Field(default_factory=list)

class ActivityRules(BaseModel):
    rules: Dict[ActivityCategory, CategoryRule]
    default: DefaultRule
    metadata: RulesMetadata
    privacy: PrivacyRule = Field(default_factory=PrivacyRule)
