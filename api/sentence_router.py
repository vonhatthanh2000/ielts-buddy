from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from schemas import SentenceCorrectResponse, SentenceRequest
from db.supabase_client import get_supabase
from services.sentence_service import correct_sentence

router = APIRouter(prefix="/v1/sentence", tags=["sentence"])


@router.post("/correct", response_model=SentenceCorrectResponse)
def sentence_correct(
    body: SentenceRequest, supabase: Client = Depends(get_supabase)
) -> SentenceCorrectResponse:
    try:
        raw = correct_sentence(body.text.strip(), supabase)
        return SentenceCorrectResponse.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
