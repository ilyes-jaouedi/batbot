import argparse
import asyncio
import os
import time
from typing import Optional
from dotenv import load_dotenv

from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich.rule import Rule
from rich.theme import Theme
from rich.spinner import Spinner
from rich.padding import Padding

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from agent.root_agent import create_root_agent
from runner.app_runner import run_interaction
from runner.local_session_service import LocalPickleSessionService

# Load environment variables
load_dotenv()

THEME = Theme({
    "agent.name":      "bold cyan",
    "agent.tool_call": "yellow",
    "agent.tool_name": "bold cyan",
    "agent.tool_done": "green",
    "user.name":       "bold green",
    "error":           "bold red",
    "info":            "dim white",
    "elapsed":         "dim cyan italic",
})

console = Console(theme=THEME, highlight=False)

PROMPT_STYLE = Style.from_dict({
    "prompt": "ansigreen bold",
})


class TerminalUI:
    def __init__(self, console: Console):
        self.console = console
        self.accumulated_text = ""
        self.live: Optional[Live] = None
        self.tool_log: list[tuple[str, str]] = []   # (name, args_preview)
        self.current_tool: Optional[str] = None
        self._pending_args: dict[str, str] = {}     # function_call name -> preview
        self.responding = False

    def reset(self):
        self.accumulated_text = ""
        self.tool_log = []
        self.current_tool = None
        self._pending_args = {}
        self.responding = False

    def _renderable(self):
        items = []

        # Completed tool calls
        for name, preview in self.tool_log:
            line = Text()
            line.append("  ✓ ", style="agent.tool_done bold")
            line.append(name, style="agent.tool_name")
            if preview:
                line.append(f"  {preview}", style="dim")
            items.append(line)

        # Active spinner: tool execution or plain thinking
        if self.current_tool:
            items.append(Spinner("dots", text=Text.from_markup(
                f"  [agent.tool_call]⚙  {self.current_tool}[/agent.tool_call]"
            )))
        elif not self.responding:
            items.append(Spinner("dots2", text=Text.from_markup(
                "  [bold yellow]Batbot is thinking...[/bold yellow]"
            )))

        # Streaming response panel
        if self.accumulated_text:
            items.append(Panel(
                Markdown(self.accumulated_text),
                title="[agent.name] Batbot [/agent.name]",
                border_style="cyan",
                padding=(0, 1),
            ))

        return Group(*items) if items else Text("")

    async def on_agent_event(self, event):
        if not event.content or not event.content.parts:
            return

        changed = False
        for part in event.content.parts:
            if part.text:
                self.accumulated_text += part.text
                self.responding = True
                self.current_tool = None
                changed = True
            elif part.function_call:
                args = part.function_call.args or {}
                preview = ""
                if args:
                    key = next(iter(args))
                    val = str(args[key])
                    preview = f'{key}="{val[:60]}{"…" if len(val) > 60 else ""}"'
                self._pending_args[part.function_call.name] = preview
                self.current_tool = f"{part.function_call.name}({preview})"
                changed = True
            elif part.function_response:
                name = part.function_response.name
                preview = self._pending_args.pop(name, "")
                self.tool_log.append((name, preview))
                self.current_tool = None
                changed = True

        if changed and self.live:
            self.live.update(self._renderable())


async def terminal_chat(debug: bool = False):
    ui = TerminalUI(console)

    # Header
    console.print()
    console.print(Rule("[bold cyan] ✦ Batbot [/bold cyan]", style="cyan"))
    console.print()

    # Init spinner (single Live, no nested Status)
    with Live(
        Spinner("dots2", text="  [bold green]Initializing...[/bold green]"),
        console=console,
        refresh_per_second=12,
    ) as live:
        agent = create_root_agent()
        session_service = LocalPickleSessionService(file_path="local_sessions.pkl")
        live.update(Text.from_markup("  [bold green]✓  Ready[/bold green]"))

    user_id = os.getenv("ALLOWED_USER_ID")
    if not user_id:
        console.print("[error]❌  ALLOWED_USER_ID not set in .env[/error]")
        return

    history_file = os.path.join(os.path.expanduser("~"), ".batbot_history")
    prompt_session = PromptSession(
        history=FileHistory(history_file),
        style=PROMPT_STYLE,
    )

    console.print(Padding(Text.from_markup(
        f"[info]session: {user_id}  ·  /clear to reset  ·  exit to quit[/info]"
    ), (0, 2)))
    console.print()

    while True:
        try:
            user_input = await prompt_session.prompt_async(
                HTML("<ansigreen><b>You ❯</b></ansigreen> "),
                auto_suggest=AutoSuggestFromHistory(),
            )
            user_input = user_input.strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                console.print()
                console.print(Rule(style="dim"))
                console.print(Padding(Text.from_markup("[info]Goodbye.[/info]"), (0, 2)))
                break

            if user_input.lower() == "/clear":
                app_name = "telegram_bot_app"
                session_id = f"session_{user_id}"
                try:
                    await session_service.delete_session(
                        app_name=app_name, user_id=user_id, session_id=session_id
                    )
                except Exception:
                    pass
                await session_service.create_session(
                    app_name=app_name, user_id=user_id, session_id=session_id
                )
                console.print(Padding(Text.from_markup("[info]✓  Session cleared[/info]"), (0, 2)))
                continue

            # --- User turn display ---
            console.print()
            console.print(Rule("[user.name] You [/user.name]", style="green", align="left"))
            console.print(Padding(Text(user_input, style="white"), (0, 2)))
            console.print()

            # --- Agent turn ---
            ui.reset()
            t0 = time.monotonic()

            with Live(
                ui._renderable(),
                console=console,
                refresh_per_second=12,
                vertical_overflow="visible",
            ) as live:
                ui.live = live
                response = await run_interaction(
                    agent,
                    session_service,
                    user_id,
                    user_input,
                    on_event=ui.on_agent_event,
                    debug=debug,
                )
                # Final static render
                live.update(Panel(
                    Markdown(response or "_(no response)_"),
                    title="[agent.name] Batbot [/agent.name]",
                    border_style="cyan",
                    padding=(0, 1),
                ))

            elapsed = time.monotonic() - t0
            console.print(Padding(
                Text.from_markup(f"[elapsed]⏱  {elapsed:.1f}s[/elapsed]"),
                (0, 2)
            ))
            console.print()

            ui.live = None

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"\n[error]❌  {e}[/error]")
            if debug:
                import traceback
                console.print(f"[error]{traceback.format_exc()}[/error]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    try:
        asyncio.run(terminal_chat(debug=args.debug))
    except (KeyboardInterrupt, EOFError):
        console.print("\n[info]Goodbye.[/info]")
