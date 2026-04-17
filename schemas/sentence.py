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


class ImprovementItem(BaseModel):
    """One natural phrase improvement for revision."""

    model_config = ConfigDict(extra="ignore")

    original_phrase: str = Field(
        ...,
        description="Original phrasing that could be more natural",
        examples=["I want to find"],
    )
    improved_phrase: str = Field(
        ...,
        description="More natural, idiomatic alternative expressing the same meaning",
        examples=["I am looking for"],
    )
    explanation: Optional[str] = Field(
        None,
        description="Why the improved version sounds more natural",
    )


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
    improvements: List[ImprovementItem] = Field(
        default_factory=list,
        description="Natural phrase improvements for revision (e.g., 'I want to find' -> 'I am looking for').",
    )
    tip: Optional[str] = Field(None, description="One short improvement tip.")


class BatchAnalysisRequest(BaseModel):
    """Request to generate a batch analysis of unreviewed sentences."""

    max_sentences: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of unanalyzed sentences to include in the report",
    )


class BatchAnalysisResponse(BaseModel):
    """Response containing a generated markdown analysis report."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique identifier for this analysis")
    content: str = Field(..., description="Full markdown content for frontend display")
    created_at: str = Field(..., description="Timestamp when the analysis was created")


class SentenceHistoryItem(BaseModel):
    """One saved sentence row (list view; no nested mistakes)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    created_at: Optional[str] = None
    original: str
    corrected: str
    natural: str
    has_mistakes: bool


class SentenceHistoryResponse(BaseModel):
    items: List[SentenceHistoryItem]
    total: int
    page: int = Field(..., description="0-based page index echoed from the request.")
    page_size: int
