from phi.agent import Agent
from phi.model.openai import OpenAIChat

from config import SENTENCE_AGENT_DESCRIPTION
from config import SENTENCE_AGENT_INSTRUCTIONS
from config import SENTENCE_AGENT_EXPECTED_OUTPUT

sentence_agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    description=SENTENCE_AGENT_DESCRIPTION,
    instructions=SENTENCE_AGENT_INSTRUCTIONS,
    expected_output=SENTENCE_AGENT_EXPECTED_OUTPUT,
    markdown=True,
    debug_mode=True,
)
sentence_agent.print_response("Today is beautiful", stream=True)


