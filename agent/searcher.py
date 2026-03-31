import os
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.adk.models import Gemini
from .config import GEMINI_MODEL_NAME, RETRY_OPTIONS, SEARCH_AGENT_INSTRUCTIONS

_use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
_api_key    = os.getenv("GOOGLE_API_KEY")

def create_search_agent() -> LlmAgent:
    if _use_vertex:
        model = Gemini(model=GEMINI_MODEL_NAME, retry_options=RETRY_OPTIONS)
    elif _api_key:
        model = Gemini(model=GEMINI_MODEL_NAME, api_key=_api_key, retry_options=RETRY_OPTIONS)
    else:
        raise EnvironmentError(
            "No auth configured. Set GOOGLE_GENAI_USE_VERTEXAI=TRUE (+ GOOGLE_CLOUD_PROJECT) "
            "or GOOGLE_API_KEY in your .env file."
        )

    return LlmAgent(
        name="search_agent",
        model=model,
        description="Delegates to this agent when you need to search the internet for current facts, news, or external knowledge.",
        instruction=SEARCH_AGENT_INSTRUCTIONS,
        tools=[google_search]
    )
