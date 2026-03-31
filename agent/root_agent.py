from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.tools import FunctionTool, AgentTool
from google.adk.models.anthropic_llm import Claude
from google.adk.models.registry import LLMRegistry
from .tools import (
    write_to_file, read_file, replace_in_file, run_shell_command, 
    get_current_time, ingest_knowledge_base, search_knowledge_base,
    fetch_webpage_text, download_pdf_from_url, search_arxiv,
    search_ieee, get_ieee_full_text, approve_action, reject_action,
    read_phd_emails, send_phd_email, search_phd_emails,
    log_to_journal, read_journal
)
from .searcher import create_search_agent
from .config import MODEL_NAME, RETRY_OPTIONS, ROOT_AGENT_INSTRUCTIONS



import functools

def sanitize_output(func):
    """Decorator to sanitize string outputs of tool functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, str):
            return "".join(c for c in result if not 0xD800 <= ord(c) <= 0xDFFF)
        return result
    return wrapper

def create_root_agent() -> LlmAgent:
    # 1. Create the subagent
    search_subagent = create_search_agent()
    
    # 2. Wrap the subagent as an AgentTool
    search_subagent_tool = AgentTool(agent=search_subagent)
    
    # 3. Wrap all functions as FunctionTools
    tools_to_wrap = [
        write_to_file, read_file, replace_in_file, run_shell_command, 
        get_current_time, ingest_knowledge_base, search_knowledge_base,
        fetch_webpage_text, download_pdf_from_url, search_arxiv,
        search_ieee, get_ieee_full_text, approve_action, reject_action,
        read_phd_emails, send_phd_email, search_phd_emails,
        log_to_journal, read_journal
    ]
    
    tools = [search_subagent_tool]
    for func in tools_to_wrap:
        tools.append(FunctionTool(func=sanitize_output(func)))

    # 4. Initialize the Root Agent with wrapped tools and subagents
    return LlmAgent(
        name="Batbot",
        model=Gemini(
            model=MODEL_NAME,
            retry_options=RETRY_OPTIONS
        ),
        instruction=ROOT_AGENT_INSTRUCTIONS,
        tools=tools,
        sub_agents=[search_subagent] # Pass the raw agent instance, not the tool wrapper
    )
