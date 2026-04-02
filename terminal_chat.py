import argparse
import asyncio
import os
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.status import Status
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich.theme import Theme

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from agent.root_agent import create_root_agent
from runner.app_runner import run_interaction
from runner.local_session_service import LocalPickleSessionService

# Load environment variables
load_dotenv()

# Custom theme for better visual distinction
custom_theme = Theme({
    "agent.name": "bold cyan",
    "agent.text": "white",
    "agent.tool_call": "bold blue",
    "agent.tool_name": "cyan",
    "agent.tool_done": "bold green",
    "user.name": "bold green",
    "user.text": "white",
    "error": "bold red",
    "info": "italic magenta"
})

console = Console(theme=custom_theme)

class TerminalUI:
    def __init__(self, console):
        self.console = console
        self.status = None
        self.accumulated_text = ""
        self.live = None

    async def on_agent_event(self, event):
        if not event.content or not event.content.parts:
            return

        for part in event.content.parts:
            if part.text:
                # Accumulate text for the final markdown render
                self.accumulated_text += part.text
                if self.live:
                    self.live.update(Panel(
                        Markdown(self.accumulated_text),
                        title="[agent.name]Batbot[/agent.name]",
                        border_style="cyan",
                        expand=False
                    ))
            elif part.function_call:
                self.console.print(f"[agent.tool_call]🛠️  Calling Tool:[/agent.tool_call] [agent.tool_name]{part.function_call.name}[/agent.tool_name]")
                if self.status:
                    self.status.update(status=f"[agent.tool_call]Executing {part.function_call.name}...[/agent.tool_call]")
            elif part.function_response:
                # We can't easily see the response content here without knowing its structure,
                # but we can acknowledge it's done.
                self.console.print(f"[agent.tool_done]✅ Tool [agent.tool_name]{part.function_response.name}[/agent.tool_name] finished.[/agent.tool_done]")
                if self.status:
                    self.status.update(status="[bold yellow]Batbot is thinking...[/bold yellow]")

async def terminal_chat(debug: bool = False):
    ui = TerminalUI(console)
    
    # 1. Initialize agent and session service
    with Status("[bold green]Initializing Batbot...[/bold green]", console=console) as status:
        agent = create_root_agent()
        session_service = LocalPickleSessionService(file_path="local_sessions.pkl")
    
    # 2. Setup user context
    user_id = os.getenv("ALLOWED_USER_ID")
    if not user_id:
        console.print("[error]❌ Error: ALLOWED_USER_ID not found in .env.[/error]")
        return

    # 3. Setup prompt-toolkit session for history and better input
    # Ensure history directory exists
    history_file = os.path.join(os.path.expanduser("~"), ".batbot_history")
    session = PromptSession(history=FileHistory(history_file))

    console.print(Panel(
        Text(f"Context: User {user_id}\nType 'exit' or 'quit' to stop.\nHistory is saved to {history_file}", justify="center"),
        title="[agent.name]Batbot Terminal Chat[/agent.name]",
        border_style="magenta"
    ))

    while True:
        try:
            # 4. Get input with history support
            user_input = await session.prompt_async(
                [("class:user.name", "You: ")],
                auto_suggest=AutoSuggestFromHistory()
            )
            user_input = user_input.strip()
            
            if user_input.lower() == "/clear":
                session_id = f"session_{user_id}"
                app_name = "telegram_bot_app"
                try:
                    # Try to delete if it exists
                    await session_service.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)
                except Exception:
                    pass
                await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
                console.print("[info]🧹 Session history cleared.[/info]")
                continue

            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue

            # 5. Run interaction
            ui.accumulated_text = ""
            with Status("[bold yellow]Batbot is thinking...[/bold yellow]", console=console) as status:
                ui.status = status
                # Create a Live display for streaming Markdown
                with Live(Panel(Text("..."), title="[agent.name]Batbot[/agent.name]", border_style="cyan"), 
                           console=console, refresh_per_second=4, vertical_overflow="visible") as live:
                    ui.live = live
                    response = await run_interaction(
                        agent,
                        session_service,
                        user_id,
                        user_input,
                        on_event=ui.on_agent_event,
                        debug=debug
                    )
                    # Final update to ensure everything is rendered
                    live.update(Panel(
                        Markdown(response),
                        title="[agent.name]Batbot[/agent.name]",
                        border_style="cyan"
                    ))
            
            ui.live = None
            ui.status = None

        except KeyboardInterrupt:
            continue # Allow Ctrl+C to clear the line
        except EOFError:
            break # Ctrl+D to exit
        except Exception as e:
            import traceback
            console.print(f"\n[error]❌ Error: {e}[/error]")
            console.print(f"[error]{traceback.format_exc()}[/error]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    try:
        asyncio.run(terminal_chat(debug=args.debug))
    except (KeyboardInterrupt, EOFError):
        console.print("\n[error]Exiting...[/error]")
