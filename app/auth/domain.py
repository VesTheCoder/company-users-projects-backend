from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CurrentPrincipal:
    user_id: UUID
    session_id: UUID
    csrf_token: bytes
    expires_at: datetime
    login: str
    display_name: str
