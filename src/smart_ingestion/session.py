import uuid
from dataclasses import dataclass, field

from smart_ingestion.models import ExecutionPlan, IngestionIntent, SessionState


@dataclass
class Session:
    session_id: str
    state: SessionState = SessionState.IDLE
    intent: IngestionIntent = field(default_factory=IngestionIntent)
    selected_agent_id: str | None = None
    plan: ExecutionPlan | None = None
    pending_field: str | None = None
    history: list[tuple[str, str]] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        new_id = session_id or str(uuid.uuid4())
        session = Session(session_id=new_id)
        self._sessions[new_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def reset_flow(self, session: Session) -> None:
        session.state = SessionState.IDLE
        session.intent = IngestionIntent()
        session.selected_agent_id = None
        session.plan = None
        session.pending_field = None


session_store = SessionStore()
