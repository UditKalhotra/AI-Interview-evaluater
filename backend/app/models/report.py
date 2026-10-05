"""reports collection."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .mongo_types import PyObjectId


class QuestionReportItem(BaseModel):
    question_id: str
    question_text: str
    topic: str
    difficulty: str
    transcript: Optional[str] = ""
    response_time_seconds: Optional[float] = 0.0
    correctness_score: Optional[float] = None
    behavior_score: Optional[float] = None
    behavior_explanation: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    missed_rubric_points: List[str] = Field(default_factory=list)


class TopicReportItem(BaseModel):
    topic: str
    question_count: int
    avg_correctness_score: float
    avg_behavior_score: float
    avg_combined_score: float


class SessionReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    session_id: str
    status: str = "complete"
    overall_technical_score: float = 0.0
    overall_communication_score: float = 0.0
    overall_score: float = 0.0
    total_questions_answered: int = 0
    per_question_breakdown: List[QuestionReportItem] = Field(default_factory=list)
    topic_breakdown: List[TopicReportItem] = Field(default_factory=list)
    chart_data: Dict[str, Any] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
