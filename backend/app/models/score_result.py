"""score_results collection."""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from .mongo_types import PyObjectId


class Features(BaseModel):
    """Embedded document on score_results — populated starting Module 5."""

    fillers: Optional[int] = None
    pauses: Optional[dict] = None  # e.g. {"count": int, "total_duration_seconds": float, "long_pauses_count": int}
    speaking_rate: Optional[float] = None  # words per minute
    repetitions: Optional[int] = None
    asked_repeat: Optional[bool] = False



class ScoreResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    answer_id: str
    correctness_score: Optional[float] = None  # populated Module 7
    behavior_score: Optional[float] = None  # populated Module 6
    behavior_explanation: Optional[str] = None  # populated Module 6
    explanation: Optional[str] = None  # alias/shortcut
    features: Optional[Features] = None  # populated Module 5
