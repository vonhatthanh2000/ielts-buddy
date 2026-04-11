from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.connection import get_db
from services.sentence_service import correct_sentence

router = APIRouter(prefix="/v1/sentence", tags=["sentence"])


class SentenceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000, description="Sentence to correct.")


@router.post("/correct")
def sentence_correct(body: SentenceRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return correct_sentence(body.text.strip(), db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
