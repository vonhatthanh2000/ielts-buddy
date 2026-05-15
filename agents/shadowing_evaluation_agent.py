# SHADOWING — disabled. Only used when shadowing routes are enabled in main.py.

from phi.agent import Agent
from phi.model.openai import OpenAIChat

SHADOWING_AGENT_DESCRIPTION = """
You are a simple shadowing evaluator. You compare what the user said with the expected sentence and report how similar they are.

You only look at the text transcript - not audio quality or pronunciation details. Just: did they say the right words?
"""


SHADOWING_AGENT_INSTRUCTIONS = [
    "Compare the TARGET sentence with the USER's transcript.",

    "Calculate one SIMILARITY SCORE (0-100) based on:",
    "  - Exact word matches (highest weight)",
    "  - Similar words (e.g., 'actually' vs 'acually')",
    "  - Missing words (penalty)",
    "  - Extra words like 'um', 'uh' (small penalty)",

    "List the DIFFERENCES found:",
    "  - For each word that differs, show: expected word → what user said",
    "  - If word was missed, show: expected word → [missing]",
    "  - If extra word added, show: [extra] → extra word",

    "Give brief feedback (2-3 sentences max):",
    "  - Overall how close it was",
    "  - One specific thing to improve next time",
]


SHADOWING_AGENT_EXPECTED_OUTPUT = """
Return output in strict JSON format:

{
  "similarity_score": <number 0-100>,
  "differences": [
    {
      "expected": "<word from target sentence>",
      "actual": "<what user said, or [missing] if omitted>"
    }
  ],
  "feedback": "<brief feedback, 2-3 sentences>"
}

Constraints:
- JSON must be valid with no markdown formatting
- similarity_score: 0-100 integer (100 = perfect match)
- differences: array of word-level differences (can be empty if perfect)
- feedback: max 3 sentences, encouraging but honest
- If user transcript is empty, score is 0 and feedback says "No speech detected"
"""


shadowing_evaluation_agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    description=SHADOWING_AGENT_DESCRIPTION,
    instructions=SHADOWING_AGENT_INSTRUCTIONS,
    expected_output=SHADOWING_AGENT_EXPECTED_OUTPUT,
    markdown=False,
)
