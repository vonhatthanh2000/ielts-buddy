"""Speech recording and evaluation domain models."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrengthItem(BaseModel):
    """One identified strength in the speech."""

    model_config = ConfigDict(extra="ignore")

    point: str = Field(..., description="What was done well.")
    example: str = Field(..., description="Specific example from transcript.")


class ImprovementItem(BaseModel):
    """One area for improvement with concrete tip."""

    model_config = ConfigDict(extra="ignore")

    point: str = Field(..., description="What needs improvement.")
    example: str = Field(..., description="Specific example from transcript.")
    tip: str = Field(..., description="Concrete tip to improve this aspect.")


class SpeechEvaluationData(BaseModel):
    """Structured speech evaluation data from AI agent."""

    model_config = ConfigDict(extra="ignore")

    overall_score: int = Field(..., ge=0, le=100, description="Overall speaking score 0-100.")
    pronunciation_score: int = Field(..., ge=0, le=100, description="Pronunciation clarity score.")
    fluency_score: int = Field(..., ge=0, le=100, description="Speech flow and naturalness score.")
    grammar_score: int = Field(..., ge=0, le=100, description="Grammar accuracy score.")
    vocabulary_score: int = Field(..., ge=0, le=100, description="Vocabulary usage score.")
    strengths: List[StrengthItem] = Field(default_factory=list, description="Identified strengths.")
    improvements: List[ImprovementItem] = Field(default_factory=list, description="Areas for improvement.")
    detailed_feedback: str = Field(..., description="Overall detailed feedback.")
    learning_tip: str = Field(..., description="One practical tip for improvement.")


class SpeechUploadRequest(BaseModel):
    """Request to upload and evaluate a speech recording.

    Note: The actual audio file is uploaded via multipart/form-data,
    not as a base64 string in JSON. This model is for additional metadata.
    """

    duration_seconds: Optional[int] = Field(
        None,
        ge=1,
        le=600,
        description="Duration of the recording in seconds (max 10 minutes).",
    )


class SpeechEvaluationResponse(BaseModel):
    """Response containing speech recording and evaluation results."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique ID of the speech recording.")
    created_at: Optional[str] = None
    audio_url: str = Field(..., description="URL to the stored audio file.")
    audio_duration_seconds: Optional[int] = None
    transcript: str = Field(..., description="Transcribed text from the audio.")
    evaluation: SpeechEvaluationData = Field(..., description="AI evaluation results.")


class SpeechHistoryItem(BaseModel):
    """One saved speech recording (list view, without full evaluation details)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    created_at: Optional[str] = None
    audio_url: str
    audio_duration_seconds: Optional[int] = None
    overall_score: Optional[int] = None
    transcript_preview: str = Field(..., description="First 100 chars of transcript.")


class SpeechHistoryResponse(BaseModel):
    """Paginated list of speech recordings."""

    items: List[SpeechHistoryItem]
    total: int
    page: int = Field(..., description="0-based page index echoed from the request.")
    page_size: int
