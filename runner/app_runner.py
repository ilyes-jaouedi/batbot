import asyncio
import traceback
from google.adk.runners import Runner, RunConfig
from google.adk.sessions import BaseSessionService
from google.genai import types
from google.adk.agents import BaseAgent

def sanitize_string(s: str) -> str:
    """Removes surrogate characters that cause JSON serialization errors."""
    if not isinstance(s, str):
        return s
    return "".join(c for c in s if not 0xD800 <= ord(c) <= 0xDFFF)

async def run_interaction(agent: BaseAgent, session_service: BaseSessionService, user_id: str, user_input: str, on_event: callable = None, debug: bool = False) -> str:
    app_name = "telegram_bot_app"
    session_id = f"session_{user_id}"

    # Sanitize user input
    user_input = sanitize_string(user_input)

    # Fetch existing session or create a new one
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    if not session:
        await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    else:
        # --- Context Trimming: trim the storage session directly ---
        # get_session() returns a copy, so we must access the underlying store.
        MAX_EVENTS = 1000
        storage_session = (
            session_service.sessions
            .get(app_name, {})
            .get(user_id, {})
            .get(session_id)
        )
        if storage_session and len(storage_session.events) > MAX_EVENTS:
            storage_session.events = storage_session.events[-MAX_EVENTS:]

            # Ensure we start on a plain user text event so Gemini never sees
            # an orphaned function_response at the head of the history.
            def _is_user_text(ev):
                if not ev.content or ev.content.role != 'user':
                    return False
                return any(hasattr(p, 'text') and p.text for p in (ev.content.parts or []))

            while storage_session.events and not _is_user_text(storage_session.events[0]):
                storage_session.events.pop(0)

            if hasattr(session_service, "_save"):
                session_service._save()

    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service
    )

    # print(f"Local Console: Passing user input to agent: {user_input}")
    content = types.Content(role='user', parts=[types.Part(text=user_input)])

    # Configure sliding window to stay under Claude's 200k limit
    run_config = RunConfig(
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(target_tokens=750000)
        )
    )

    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
        run_config=run_config
    )

    final_response = ""
    async for event in events:
        if debug:
            print(f"[DEBUG] Event type: {type(event).__name__}, is_final: {event.is_final_response()}")
            if event.content and event.content.parts:
                for i, p in enumerate(event.content.parts):
                    if hasattr(p, 'text') and p.text:
                        print(f"[DEBUG]   part[{i}] text={repr(p.text[:100])}")
                    elif hasattr(p, 'function_call') and p.function_call:
                        print(f"[DEBUG]   part[{i}] function_call={p.function_call.name} args={repr(str(p.function_call.args)[:200])}")
                    elif hasattr(p, 'function_response') and p.function_response:
                        print(f"[DEBUG]   part[{i}] function_response={p.function_response.name} response={repr(str(p.function_response.response)[:200])}")
            if hasattr(event, 'error_code') and event.error_code:
                print(f"[DEBUG] Event error_code: {event.error_code}, error_message: {getattr(event, 'error_message', '')}")

        if on_event:
            if asyncio.iscoroutinefunction(on_event):
                await on_event(event)
            else:
                on_event(event)
        else:
            # Print intermediate text parts so we can see tool calls or reasoning
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent: {part.text}")
                    elif part.function_call:
                        print(f"Agent is calling tool: {part.function_call.name}")

        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
