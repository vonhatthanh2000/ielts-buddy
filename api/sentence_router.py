from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user_id
from schemas import SentenceCorrectResponse, SentenceRequest
from supabase.client import Client, get_supabase
from services.sentence_service import correct_sentence

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
