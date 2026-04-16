import json

from supabase.client import Client

from agents.sentence_correct_agent import sentence_correct_agent
from agents.batch_analysis_agent import batch_analysis_agent


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


# ---------------------------------------------------------------------------
# Batch analysis helpers
# ---------------------------------------------------------------------------


def generate_batch_analysis(
    supabase: Client,
    user_id: str,
    max_sentences: int = 20,
) -> str:
    """
    Generate a markdown analysis report of unanalyzed sentences.

    Fetches unanalyzed sentences with their mistakes and improvements,
    calls the batch analysis agent to generate a report, saves it,
    and marks the sentences as analyzed.

    Returns the analysis ID.
    """
    # Fetch unanalyzed sentences
    sentences = _fetch_unanalyzed_sentences(supabase, user_id, max_sentences)

    if not sentences:
        raise ValueError("No unanalyzed sentences found")

    # Run batch analysis
    markdown_content = _run_batch_analysis(sentences)

    # Get sentence IDs for marking as analyzed
    sentence_ids = [s["id"] for s in sentences]

    # Save analysis (just store the markdown content)
    analysis_id = _save_analysis(supabase, user_id, markdown_content)

    # Mark sentences as analyzed
    _mark_sentences_analyzed(supabase, sentence_ids)

    return analysis_id


def _fetch_unanalyzed_sentences(
    supabase: Client, user_id: str, limit: int
) -> list[dict]:
    """Fetch unanalyzed sentences with their mistakes and improvements."""
    # Fetch unanalyzed sentences
    res = (
        supabase.table("sentences")
        .select("id, original, corrected, natural, has_mistakes, created_at")
        .eq("user_id", user_id)
        .eq("analyzed", False)
        .order("created_at", desc=False)  # Oldest first
        .limit(limit)
        .execute()
    )

    if not res.data:
        return []

    sentences = res.data
    sentence_ids = [s["id"] for s in sentences]

    # Fetch mistakes for these sentences
    mistakes_res = (
        supabase.table("sentence_mistakes")
        .select("sentence_id, type, original, fix, explanation")
        .in_("sentence_id", sentence_ids)
        .execute()
    )
    mistakes_map: dict[str, list] = {}
    for m in mistakes_res.data or []:
        sid = m["sentence_id"]
        if sid not in mistakes_map:
            mistakes_map[sid] = []
        mistakes_map[sid].append(m)

    # Fetch improvements for these sentences
    improvements_res = (
        supabase.table("sentence_improvements")
        .select("sentence_id, original_phrase, improved_phrase, explanation")
        .in_("sentence_id", sentence_ids)
        .execute()
    )
    improvements_map: dict[str, list] = {}
    for imp in improvements_res.data or []:
        sid = imp["sentence_id"]
        if sid not in improvements_map:
            improvements_map[sid] = []
        improvements_map[sid].append(imp)

    # Combine all data
    result = []
    for s in sentences:
        result.append({
            "id": s["id"],
            "original": s["original"],
            "corrected": s["corrected"],
            "natural": s["natural"],
            "has_mistakes": s["has_mistakes"],
            "created_at": s["created_at"],
            "mistakes": mistakes_map.get(s["id"], []),
            "improvements": improvements_map.get(s["id"], []),
        })

    return result


def _run_batch_analysis(sentences: list[dict]) -> str:
    """Call the batch analysis agent with the sentences."""
    prompt = _build_batch_analysis_prompt(sentences)
    response = batch_analysis_agent.run(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _build_batch_analysis_prompt(sentences: list[dict]) -> str:
    """Build the prompt for the batch analysis agent."""
    lines = [
        f"Analyze the following {len(sentences)} sentences for review.",
        "",
        "For each sentence, I provide:",
        "- Original: what the user wrote",
        "- Corrected: grammar-fixed version",
        "- Natural: more fluent version",
        "- Mistakes: specific errors found",
        "- Improvements: natural phrase alternatives",
        "",
        "---",
        "",
    ]

    for i, s in enumerate(sentences, 1):
        lines.append(f"## Sentence {i}")
        lines.append(f"**Original**: {s['original']}")
        lines.append(f"**Corrected**: {s['corrected']}")
        lines.append(f"**Natural**: {s['natural']}")

        if s.get("mistakes"):
            lines.append("**Mistakes**:")
            for m in s["mistakes"]:
                lines.append(f"- Type: {m.get('type', 'unknown')}")
                lines.append(f"  - Original: {m.get('original', 'N/A')}")
                lines.append(f"  - Fix: {m.get('fix', 'N/A')}")
                lines.append(f"  - Explanation: {m.get('explanation', 'N/A')}")

        if s.get("improvements"):
            lines.append("**Improvements**:")
            for imp in s["improvements"]:
                lines.append(f"- '{imp.get('original_phrase')}' → '{imp.get('improved_phrase')}'")
                if imp.get("explanation"):
                    lines.append(f"  - Why: {imp['explanation']}")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _save_analysis(supabase: Client, user_id: str, content: str) -> str:
    """Save the analysis report to the database."""
    row = {
        "user_id": user_id,
        "content": content,
    }

    res = supabase.table("sentence_analyses").insert(row).execute()
    if not res.data:
        raise RuntimeError("Failed to save analysis")

    return res.data[0]["id"]


def _mark_sentences_analyzed(supabase: Client, sentence_ids: list[str]) -> None:
    """Mark the sentences as analyzed."""
    if not sentence_ids:
        return

    # Update each sentence to mark as analyzed
    # Supabase doesn't support bulk update with WHERE id IN (...) directly,
    # so we do it one by one or use RPC if needed
    for sid in sentence_ids:
        supabase.table("sentences").update({"analyzed": True}).eq("id", sid).execute()
