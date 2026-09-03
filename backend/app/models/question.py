"""
questions collection.

Mirrors Master_Question_Bank_with_topics_active.csv exactly. `rubric` is the
raw CSV string on import; Module 2's import script parses it into a list of
rubric-point strings before inserting, so the field accepts either shape.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from .mongo_types import PyObjectId


class Question(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    question_id: str
    source_question_number: str
    question: str
    topic: str
    reference_answer: str
    rubric: Union[str, List[str]]
    difficulty: str  # Easy / Medium / Hard
    irt_difficulty: float
    active: bool
