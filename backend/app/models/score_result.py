"""score_results collection."""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from .mongo_types import PyObjectId


class Features(BaseModel):
    """Embedded document on score_results — populated starting Module 5."""

    fillers: Optional[int] = None
    pauses: Optional[dict] = None  # e.g. {"count": int, "total_duration_seconds": float}
    speaking_rate: Optional[float] = None  # words per minute
    repetitions: Optional[int] = None


class ScoreResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    answer_id: str
    correctness_score: Optional[float] = None  # populated Module 7
    behavior_score: Optional[float] = None  # populated Module 6
    features: Optional[Features] = None  # populated Module 5
