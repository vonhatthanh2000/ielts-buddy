from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_profile_id
from schemas import (
    YoutubeAnalysisHistoryResponse,
    YoutubeAnalysisRequest,
    YoutubeAnalysisResponse,
)
from supabase_client import Client, get_supabase
from services.youtube_service import (
    analyze_youtube_video,
    get_youtube_analysis_detail,
    list_youtube_analyses,
)

router = APIRouter(prefix="/v1/youtube", tags=["youtube"])


@router.post("/analyze", response_model=YoutubeAnalysisResponse)
def youtube_analyze(
    body: YoutubeAnalysisRequest,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> YoutubeAnalysisResponse:
    """
    Analyze a YouTube video transcript for useful English content.

    Extracts the transcript, identifies useful sentences, grammar patterns,
    and everyday phrases for English learning.
    """
    try:
        raw = analyze_youtube_video(body.url.strip(), supabase, profile_id)
        return YoutubeAnalysisResponse.model_validate(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/history", response_model=YoutubeAnalysisHistoryResponse)
def youtube_history(
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
    page: int = Query(0, ge=0, description="First page is 0."),
    page_size: int = Query(20, ge=1, le=100),
) -> YoutubeAnalysisHistoryResponse:
    """List paginated YouTube analyses for the current profile."""
    raw = list_youtube_analyses(
        supabase, profile_id, page=page, page_size=page_size
    )
    return YoutubeAnalysisHistoryResponse.model_validate(raw)


@router.get("/{analysis_id}", response_model=YoutubeAnalysisResponse)
def youtube_analysis_detail(
    analysis_id: UUID,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> YoutubeAnalysisResponse:
    """Get detailed analysis for a specific YouTube analysis."""
    raw = get_youtube_analysis_detail(supabase, profile_id, str(analysis_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return YoutubeAnalysisResponse.model_validate(raw)
