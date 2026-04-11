import json

from sqlalchemy.orm import Session

from agents.sentence_correct_agent import sentence_correct_agent
from db.models import Sentence, SentenceMistake


def correct_sentence(text: str, db: Session) -> dict:
    """
    Full pipeline: call agent → parse output → save to DB → return result.
    """
    raw = _run_agent(text)
    parsed = _parse_output(text, raw)
    _save(parsed, db)
    return parsed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_agent(text: str) -> str:
    response = sentence_correct_agent.run(text)
    return response.content if hasattr(response, "content") else str(response)


def _parse_output(original_text: str, raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "original": original_text,
            "corrected": original_text,
            "natural": original_text,
            "has_mistakes": False,
            "mistakes": [],
            "tip": "Agent output could not be parsed.",
        }

    mistakes = data.get("mistakes", [])
    data["has_mistakes"] = len(mistakes) > 0
    return data


def _save(data: dict, db: Session) -> None:
    sentence = Sentence(
        original=data.get("original", ""),
        corrected=data.get("corrected", ""),
        natural=data.get("natural", ""),
        has_mistakes=data.get("has_mistakes", False),
        tip=data.get("tip"),
    )
    db.add(sentence)
    db.flush()  # get sentence.id before inserting mistakes

    for m in data.get("mistakes", []):
        db.add(
            SentenceMistake(
                sentence_id=sentence.id,
                type=m.get("type", ""),
                original=m.get("original"),
                fix=m.get("fix"),
                explanation=m.get("explanation"),
            )
        )

    db.commit()
