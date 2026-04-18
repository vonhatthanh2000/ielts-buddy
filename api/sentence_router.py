from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.deps import get_current_profile_id
from schemas import (
    BatchAnalysisRequest,
    SentenceCorrectResponse,
    SentenceHistoryResponse,
    SentenceRequest,
)
from supabase.client import Client, get_supabase
from services.sentence_service import (
    correct_sentence,
    generate_batch_analysis,
    get_profile_sentence_detail,
    list_profile_sentences,
)

router = APIRouter(prefix="/v1/sentence", tags=["sentence"])


@router.get("/history", response_model=SentenceHistoryResponse)
def sentence_history(
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
    page: int = Query(0, ge=0, description="First page is 0."),
    page_size: int = Query(20, ge=1, le=100),
) -> SentenceHistoryResponse:
    raw = list_profile_sentences(supabase, profile_id, page=page, page_size=page_size)
    return SentenceHistoryResponse.model_validate(raw)


@router.get("/{sentence_id}", response_model=SentenceCorrectResponse)
def sentence_detail(
    sentence_id: UUID,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> SentenceCorrectResponse:
    raw = get_profile_sentence_detail(supabase, profile_id, str(sentence_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="Sentence not found")
    return SentenceCorrectResponse.model_validate(raw)


@router.post("/correct", response_model=SentenceCorrectResponse)
def sentence_correct(
    body: SentenceRequest,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> SentenceCorrectResponse:
    try:
        raw = correct_sentence(body.text.strip(), supabase, profile_id)
        return SentenceCorrectResponse.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze", status_code=204)
def analyze_batch(
    body: BatchAnalysisRequest,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> Response:
    """
    Generate a markdown analysis report of unreviewed sentences.

    Finds sentences where `analyzed=false`, gathers all their mistakes
    and improvements, generates a comprehensive markdown report via AI,
    stores it in `sentence_analyses`, and marks the sentences as analyzed.

    Returns 204 No Content on success. The analysis is saved to the database
    and can be fetched separately if needed.
    """
    try:
        generate_batch_analysis(
            supabase,
            profile_id,
            max_sentences=body.max_sentences,
        )
        return Response(status_code=204)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
