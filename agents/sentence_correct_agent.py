from phi.agent import Agent
from phi.model.openai import OpenAIChat

from config import (
    SENTENCE_AGENT_DESCRIPTION,
    SENTENCE_AGENT_EXPECTED_OUTPUT,
    SENTENCE_AGENT_INSTRUCTIONS,
)

sentence_correct_agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    description=SENTENCE_AGENT_DESCRIPTION,
    instructions=SENTENCE_AGENT_INSTRUCTIONS,
    expected_output=SENTENCE_AGENT_EXPECTED_OUTPUT,
    markdown=False,
)
