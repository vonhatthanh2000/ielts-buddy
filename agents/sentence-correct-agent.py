import sys
import json
from pathlib import Path

# Running `python agents/sentence-correct-agent.py` only adds `agents/` to sys.path;
# project root must be on the path for `import config` (unless you ran `pip install -e .`).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from phi.agent import Agent
from phi.model.openai import OpenAIChat

from config import (
    SENTENCE_AGENT_DESCRIPTION,
    SENTENCE_AGENT_INSTRUCTIONS,
    SENTENCE_AGENT_EXPECTED_OUTPUT,
)

sentence_agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    description=SENTENCE_AGENT_DESCRIPTION,
    instructions=SENTENCE_AGENT_INSTRUCTIONS,
    expected_output=SENTENCE_AGENT_EXPECTED_OUTPUT,
    markdown=False,
    debug_mode=True,
)


def correct_sentence(text: str) -> dict:
    """
    Run the sentence correction agent and return parsed JSON.
    """

    response = sentence_agent.run(text)

    content = response.content if hasattr(response, "content") else response

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "original": text,
            "corrected": text,
            "natural": text,
            "mistakes": [],
            "tip": "Failed to parse response",
            "raw_output": content
        }
