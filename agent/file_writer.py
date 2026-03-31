from google.adk.agents import LlmAgent
from .tools import write_to_file, read_file

def create_file_writer_agent() -> LlmAgent:
    return LlmAgent(
        name="file_writer_agent",
        model="gemini-2.0-flash",
        instruction="""
        You are a helpful assistant that can write information to and read information from files.
        - To save something or write to a file, use the 'write_to_file' tool.
        - To see what is inside a file, use the 'read_file' tool.
        Always confirm once a task is completed and summarize what you've read if requested.
        """,
        tools=[write_to_file, read_file]
    )
