from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user_id
from schemas import (
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    SentenceCorrectResponse,
    SentenceRequest,
)
from supabase.client import Client, get_supabase
from services.sentence_service import correct_sentence, generate_batch_analysis

router = APIRouter(prefix="/v1/sentence", tags=["sentence"])


@router.post("/correct", response_model=SentenceCorrectResponse)
def sentence_correct(
    body: SentenceRequest,
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> SentenceCorrectResponse:
    try:
        raw = correct_sentence(body.text.strip(), supabase, user_id)
        return SentenceCorrectResponse.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze", response_model=BatchAnalysisResponse)
def analyze_batch(
    body: BatchAnalysisRequest,
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> BatchAnalysisResponse:
    """
    Generate a markdown analysis report of unreviewed sentences.

    Finds sentences where `analyzed=false`, gathers all their mistakes
    and improvements, generates a comprehensive markdown report via AI,
    stores it in `sentence_analyses`, and marks the sentences as analyzed.

    Returns the generated analysis with full markdown content.
    """
    try:
        raw = generate_batch_analysis(
            supabase,
            user_id,
            max_sentences=body.max_sentences,
        )
        return BatchAnalysisResponse.model_validate(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
