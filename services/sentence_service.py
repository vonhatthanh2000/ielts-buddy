import json

from supabase.client import Client

from agents.sentence_correct_agent import sentence_correct_agent


def correct_sentence(text: str, supabase: Client, user_id: str) -> dict:
    """
    Full pipeline: call agent → parse output → save to Supabase → return result.
    """
    raw = _run_agent(text)
    parsed = _parse_output(text, raw)
    _save(parsed, supabase, user_id)
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
            "improvements": [],
            "tip": "Agent output could not be parsed.",
        }

    mistakes = data.get("mistakes", [])
    data["has_mistakes"] = len(mistakes) > 0
    # Ensure improvements field exists (backward compatibility)
    if "improvements" not in data:
        data["improvements"] = []
    return data


def _save(data: dict, supabase: Client, user_id: str) -> None:
    row = {
        "user_id": user_id,
        "original": data.get("original", ""),
        "corrected": data.get("corrected", ""),
        "natural": data.get("natural", ""),
        "has_mistakes": data.get("has_mistakes", False),
    }
    res = supabase.table("sentences").insert(row).execute()
    if not res.data:
        raise RuntimeError("Failed to insert sentence")
    sentence_id = res.data[0]["id"]

    # Save mistakes
    mistakes = data.get("mistakes", [])
    if mistakes:
        payload = [
            {
                "sentence_id": sentence_id,
                "type": m.get("type", ""),
                "original": m.get("original"),
                "fix": m.get("fix"),
                "explanation": m.get("explanation"),
            }
            for m in mistakes
        ]
        supabase.table("sentence_mistakes").insert(payload).execute()

    # Save improvements (natural phrase alternatives)
    improvements = data.get("improvements", [])
    if improvements:
        improvement_payload = [
            {
                "sentence_id": sentence_id,
                "original_phrase": imp.get("original_phrase", ""),
                "improved_phrase": imp.get("improved_phrase", ""),
                "explanation": imp.get("explanation"),
                "context": data.get("original", ""),
            }
            for imp in improvements
        ]
        supabase.table("sentence_improvements").insert(improvement_payload).execute()
