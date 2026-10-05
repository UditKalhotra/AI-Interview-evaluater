"""sessions collection."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from .mongo_types import PyObjectId


class Session(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    topic: Optional[str] = None
    current_question_id: Optional[str] = None
    status: str = "not_started"  # not_started / in_progress / complete
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
