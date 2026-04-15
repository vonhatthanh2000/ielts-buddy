from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from db.supabase_client import get_supabase
from services.sentence_service import correct_sentence

router = APIRouter(prefix="/v1/sentence", tags=["sentence"])


class SentenceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000, description="Sentence to correct.")


@router.post("/correct")
def sentence_correct(body: SentenceRequest, supabase: Client = Depends(get_supabase)) -> dict:
    try:
        return correct_sentence(body.text.strip(), supabase)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
