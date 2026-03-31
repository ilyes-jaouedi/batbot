import asyncio
import os
from dotenv import load_dotenv

from agent.root_agent import create_root_agent
from runner.app_runner import run_interaction
from runner.local_session_service import LocalPickleSessionService

# Load environment variables
load_dotenv()

async def main():
    # 1. Initialize the agent and memory
    agent = create_root_agent()
    session_service = LocalPickleSessionService()
    
    # 2. Define user input
    target_file = "cat_poem_refactored.txt"
    user_input = f"Write a short poem about a cat to a file named '{target_file}'"
    user_id = "test_local_user"
    
    # 3. Run the interaction
    await run_interaction(agent, session_service, user_id, user_input)

    # 4. Verify output
    if os.path.exists(target_file):
        print(f"\n[Verification] '{target_file}' was successfully created!")
        with open(target_file, "r") as f:
            print(f"File content:\n---\n{f.read()}\n---")
    else:
        print(f"\n[Verification] '{target_file}' was NOT found.")

if __name__ == "__main__":
    asyncio.run(main())
