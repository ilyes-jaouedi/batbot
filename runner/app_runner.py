import asyncio
from google.adk.runners import Runner, RunConfig
from google.adk.sessions import BaseSessionService
from google.genai import types
from google.adk.agents import BaseAgent

def sanitize_string(s: str) -> str:
    """Removes surrogate characters that cause JSON serialization errors."""
    if not isinstance(s, str):
        return s
    return "".join(c for c in s if not 0xD800 <= ord(c) <= 0xDFFF)

async def run_interaction(agent: BaseAgent, session_service: BaseSessionService, user_id: str, user_input: str, on_event: callable = None) -> str:
    app_name = "telegram_bot_app"
    session_id = f"session_{user_id}"

    # Sanitize user input
    user_input = sanitize_string(user_input)

    # Fetch existing session or create a new one
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    if not session:
        # print(f"Creating new session for user {user_id}")
        await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    else:
        # print(f"Reusing existing session for user {user_id}")
        
        # --- Context Trimming: Prevent Context Too Long Error ---
        MAX_EVENTS = 500
        if session.events and len(session.events) > MAX_EVENTS:
            # print(f"Local Console: Trimming session history from {len(session.events)} down to {MAX_EVENTS} events.")
            session.events = session.events[-MAX_EVENTS:]
            
            # For Claude, it's safer if the first message in the history is from the user
            while session.events and (not session.events[0].content or session.events[0].content.role != 'user'):
                session.events.pop(0)
                
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
