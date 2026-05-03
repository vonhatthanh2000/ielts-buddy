"""YouTube speech analysis domain models."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class YoutubeAnalysisRequest(BaseModel):
    """Request to analyze a YouTube video transcript."""

    url: str = Field(
        ...,
        min_length=10,
        description="YouTube video URL to analyze.",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class UsefulSentenceItem(BaseModel):
    """One useful sentence extracted from the transcript."""

    model_config = ConfigDict(extra="ignore")

    sentence: str = Field(..., description="The sentence from the transcript.")
    why_useful: str = Field(..., description="Why this sentence is worth learning.")
    grammar_pattern: str = Field(..., description="Key grammar pattern demonstrated.")
    usage_context: str = Field(..., description="When learners might use this.")


class GrammarPatternItem(BaseModel):
    """One grammar pattern identified in the transcript."""

    model_config = ConfigDict(extra="ignore")

    pattern: str = Field(..., description="Name of the grammar pattern.")
    example: str = Field(..., description="Example from the transcript.")
    usage: str = Field(..., description="When to use this pattern.")


class EverydayPhraseItem(BaseModel):
    """One everyday phrase or expression."""

    model_config = ConfigDict(extra="ignore")

    phrase: str = Field(..., description="The natural phrase or expression.")
    meaning: str = Field(..., description="What the phrase means.")
    usage_context: str = Field(..., description="Sample situation for using this phrase.")


class TranscriptSegmentItem(BaseModel):
    """One timed sentence (or clause) for shadowing playback."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., description="Transcript text for this span.")
    start_time: float = Field(..., description="Start offset in seconds from the start of the video.")
    end_time: float = Field(..., description="End offset in seconds from the start of the video.")


class YoutubeAnalysisResponse(BaseModel):
    """Response containing YouTube transcript analysis."""

    model_config = ConfigDict(extra="ignore")

    video_title: str = Field(..., description="Title of the video (if available).")
    video_url: str = Field(..., description="The YouTube URL that was analyzed.")
    transcript: str = Field(..., description="The full transcript text extracted from the video.")
    transcript_segments: List[TranscriptSegmentItem] = Field(
        default_factory=list,
        description="Transcript split into timed sentences for shadowing.",
    )
    useful_sentences: List[UsefulSentenceItem] = Field(
        default_factory=list,
        description="Useful sentences demonstrating natural spoken English.",
    )
    grammar_patterns: List[GrammarPatternItem] = Field(
        default_factory=list,
        description="Grammar patterns used in the transcript.",
    )
    everyday_phrases: List[EverydayPhraseItem] = Field(
        default_factory=list,
        description="Everyday phrases and expressions for daily conversation.",
    )
    learning_tip: Optional[str] = Field(
        None,
        description="One practical tip for improving spoken English.",
    )


class YoutubeAnalysisHistoryItem(BaseModel):
    """One saved YouTube analysis row (list view)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    created_at: Optional[str] = None
    video_title: str
    video_url: str
    sentence_count: int = Field(..., description="Number of useful sentences extracted.")
    phrase_count: int = Field(..., description="Number of everyday phrases extracted.")


class YoutubeAnalysisHistoryResponse(BaseModel):
    """Paginated list of YouTube analyses."""

    items: List[YoutubeAnalysisHistoryItem]
    total: int
    page: int = Field(..., description="0-based page index echoed from the request.")
    page_size: int
