from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.adk.models import Gemini
from .config import GEMINI_MODEL_NAME, RETRY_OPTIONS, SEARCH_AGENT_INSTRUCTIONS

def create_search_agent() -> LlmAgent:
    return LlmAgent(
        name="search_agent",
        model=Gemini(
            model=GEMINI_MODEL_NAME,
            retry_options=RETRY_OPTIONS
        ),
        description="Delegates to this agent when you need to search the internet for current facts, news, or external knowledge.",
        instruction=SEARCH_AGENT_INSTRUCTIONS,
        tools=[google_search]
    )
