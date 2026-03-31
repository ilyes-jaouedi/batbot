import os
import pickle
import logging
from typing import Optional, Any

from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions import Session
from google.adk.events import Event

logger = logging.getLogger(__name__)

class LocalPickleSessionService(InMemorySessionService):
    """
    A persistent session service that saves InMemorySessionService state 
    to a local pickle file, allowing the bot to remember context across restarts.
    """
    def __init__(self, file_path="local_sessions.pkl"):
        super().__init__()
        self.file_path = file_path
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "rb") as f:
                    data = pickle.load(f)
                    self.sessions = data.get("sessions", {})
                    self.user_state = data.get("user_state", {})
                    self.app_state = data.get("app_state", {})
                logger.info(f"Loaded persistent sessions from {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")

    def _save(self):
        try:
            with open(self.file_path, "wb") as f:
                data = {
                    "sessions": self.sessions,
                    "user_state": self.user_state,
                    "app_state": self.app_state
                }
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save sessions to disk: {e}")

    # Override the underlying implementation methods to save after mutating state
    def _create_session_impl(self, **kwargs) -> Session:
        session = super()._create_session_impl(**kwargs)
        self._save()
        return session

    def _delete_session_impl(self, **kwargs) -> None:
        super()._delete_session_impl(**kwargs)
        self._save()

    async def append_event(self, session: Session, event: Event) -> Event:
        result = await super().append_event(session, event)
        self._save()
        return result
