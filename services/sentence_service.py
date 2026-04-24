import json
from typing import Optional

from supabase.client import Client

from agents.sentence_correct_agent import sentence_correct_agent
from agents.batch_analysis_agent import batch_analysis_agent


def correct_sentence(text: str, supabase: Client, profile_id: str) -> dict:
    """
    Full pipeline: call agent → parse output → save to Supabase → return result.
    """
    raw = _run_agent(text)
    parsed = _parse_output(text, raw)
    _save(parsed, supabase, profile_id)
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


def _save(data: dict, supabase: Client, profile_id: str) -> None:
    row = {
        "profile_id": profile_id,
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
# History & detail (read)
# ---------------------------------------------------------------------------


def list_profile_sentences(
    supabase: Client,
    profile_id: str,
    *,
    page: int = 0,
    page_size: int = 20,
) -> dict:
    """Paginated sentences for a profile, newest first. ``page`` is 0-based."""
    page = max(0, page)
    page_size = min(max(1, page_size), 100)
    offset = page * page_size
    end = offset + page_size - 1

    res = (
        supabase.table("sentences")
        .select(
            "id, created_at, original, corrected, natural, has_mistakes, analyzed",
            count="exact",
        )
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .range(offset, end)
        .execute()
    )
    rows = res.data or []
    total = int(res.count) if res.count is not None else len(rows)
    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_profile_sentence_detail(
    supabase: Client,
    profile_id: str,
    sentence_id: str,
) -> Optional[dict]:
    """
    Load one sentence with mistakes and improvements, same shape as ``correct_sentence``
    output (``tip`` always ``None`` here; not persisted).
    """
    sres = (
        supabase.table("sentences")
        .select("id, original, corrected, natural, has_mistakes")
        .eq("id", sentence_id)
        .eq("profile_id", profile_id)
        .limit(1)
        .execute()
    )
    if not sres.data:
        return None
    row = sres.data[0]

    mres = (
        supabase.table("sentence_mistakes")
        .select("type, original, fix, explanation")
        .eq("sentence_id", sentence_id)
        .execute()
    )
    ires = (
        supabase.table("sentence_improvements")
        .select("original_phrase, improved_phrase, explanation")
        .eq("sentence_id", sentence_id)
        .execute()
    )

    mistakes = []
    for m in mres.data or []:
        mistakes.append({
            "type": m.get("type") or "",
            "original": m.get("original"),
            "fix": m.get("fix"),
            "explanation": m.get("explanation"),
        })

    improvements = []
    for imp in ires.data or []:
        improvements.append({
            "original_phrase": imp.get("original_phrase") or "",
            "improved_phrase": imp.get("improved_phrase") or "",
            "explanation": imp.get("explanation"),
        })

    return {
        "original": row.get("original", ""),
        "corrected": row.get("corrected", ""),
        "natural": row.get("natural", ""),
        "has_mistakes": bool(row.get("has_mistakes", False)),
        "mistakes": mistakes,
        "improvements": improvements,
        "tip": None,
    }


# ---------------------------------------------------------------------------
# Batch analysis helpers
# ---------------------------------------------------------------------------


def generate_batch_analysis(
    supabase: Client,
    profile_id: str,
    max_sentences: int = 20,
) -> dict:
    """
    Generate a markdown analysis report of unanalyzed sentences.

    Fetches unanalyzed sentences with their mistakes and improvements,
    calls the batch analysis agent to generate a report, saves it,
    and marks the sentences as analyzed.

    Returns the saved analysis payload.
    """
    # Fetch unanalyzed sentences
    sentences = _fetch_unanalyzed_sentences(supabase, profile_id, max_sentences)

    if not sentences:
        raise ValueError("No unanalyzed sentences found")

    # Run batch analysis
    markdown_content = _run_batch_analysis(sentences)

    # Get sentence IDs for marking as analyzed
    sentence_ids = [s["id"] for s in sentences]

    # Save analysis (just store the markdown content)
    analysis = _save_analysis(supabase, profile_id, markdown_content)

    # Mark sentences as analyzed
    _mark_sentences_analyzed(supabase, sentence_ids)

    return analysis


def _fetch_unanalyzed_sentences(
    supabase: Client, profile_id: str, limit: int
) -> list[dict]:
    """Fetch unanalyzed sentences with their mistakes and improvements."""
    # Fetch unanalyzed sentences
    res = (
        supabase.table("sentences")
        .select("id, original, corrected, natural, has_mistakes, created_at")
        .eq("profile_id", profile_id)
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


def _save_analysis(supabase: Client, profile_id: str, content: str) -> dict:
    """Save the analysis report to the database."""
    row = {
        "profile_id": profile_id,
        "content": content,
    }

    res = supabase.table("sentence_analyses").insert(row).execute()
    if not res.data:
        raise RuntimeError("Failed to save analysis")

    inserted = res.data[0]
    analysis_id = inserted.get("id")
    if not analysis_id:
        raise RuntimeError("Saved analysis is missing id")

    detail = (
        supabase.table("sentence_analyses")
        .select("id, content, created_at")
        .eq("id", analysis_id)
        .eq("profile_id", profile_id)
        .limit(1)
        .execute()
    )
    if not detail.data:
        raise RuntimeError("Saved analysis could not be loaded")

    return detail.data[0]


def _mark_sentences_analyzed(supabase: Client, sentence_ids: list[str]) -> None:
    """Mark the sentences as analyzed."""
    if not sentence_ids:
        return

    # Update each sentence to mark as analyzed
    # Supabase doesn't support bulk update with WHERE id IN (...) directly,
    # so we do it one by one or use RPC if needed
    for sid in sentence_ids:
        supabase.table("sentences").update({"analyzed": True}).eq("id", sid).execute()


def list_profile_sentence_analyses(
    supabase: Client,
    profile_id: str,
    *,
    page: int = 0,
    page_size: int = 20,
) -> dict:
    """Paginated sentence batch analyses for a profile, newest first."""
    page = max(0, page)
    page_size = min(max(1, page_size), 100)
    offset = page * page_size
    end = offset + page_size - 1

    res = (
        supabase.table("sentence_analyses")
        .select("id, content, created_at", count="exact")
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .range(offset, end)
        .execute()
    )
    rows = res.data or []
    total = int(res.count) if res.count is not None else len(rows)
    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_profile_sentence_analysis_detail(
    supabase: Client,
    profile_id: str,
    analysis_id: str,
) -> Optional[dict]:
    """Load one sentence batch analysis for a profile."""
    res = (
        supabase.table("sentence_analyses")
        .select("id, content, created_at")
        .eq("id", analysis_id)
        .eq("profile_id", profile_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0]
