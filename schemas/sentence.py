"""Sentence correction domain models (API, services, agents)."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SentenceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000, description="Sentence to correct.")


class SentenceMistakeItem(BaseModel):
    """One mistake from the correction agent."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(
        default="",
        description="grammar, word_choice, or fluency",
        examples=["grammar"],
    )
    original: Optional[str] = Field(None, description="Incorrect fragment from the sentence.")
    fix: Optional[str] = Field(None, description="Corrected form.")
    explanation: Optional[str] = Field(None, description="Short explanation (B1–B2 level).")


class SentenceCorrectResponse(BaseModel):
    """Successful sentence correction payload (matches agent JSON + has_mistakes)."""

    model_config = ConfigDict(extra="ignore")

    original: str
    corrected: str
    natural: str
    has_mistakes: bool = Field(..., description="True when mistakes list is non-empty.")
    mistakes: List[SentenceMistakeItem] = Field(
        default_factory=list,
        description="Identified issues; empty if the sentence is already fine.",
    )
    tip: Optional[str] = Field(None, description="One short improvement tip.")
