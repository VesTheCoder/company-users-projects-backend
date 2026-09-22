import hashlib
import hmac
import json
from datetime import datetime
from uuid import UUID

from app.exceptions.base import AppError
from app.utils.security import decode_token, encode_token, keyed_digest


class CursorCodec:
    def __init__(self, secret: str):
        self.secret = secret

    def scope(self, resource: str, company_id: str, filters: dict) -> dict:
        return {
            "v": 1,
            "resource": resource,
            "company_id": str(company_id),
            "sort": "assigned_at_desc"
            if resource == "assignments"
            else "created_at_desc",
            "filters_hash": hashlib.sha256(
                json.dumps(filters, sort_keys=True).encode()
            ).hexdigest(),
        }

    def encode(self, scope: dict, timestamp: datetime, identifier: UUID) -> str:
        payload = json.dumps(
            scope
            | {"after": {"created_at": timestamp.isoformat(), "id": str(identifier)}},
            sort_keys=True,
            separators=(",", ":"),
        )
        return encode_token(payload.encode()) + "." + keyed_digest(self.secret, payload)

    def decode(self, value: str, scope: dict) -> tuple[datetime, UUID]:
        try:
            if len(value) > 2048:
                raise ValueError
            encoded, signature = value.split(".")
            payload = decode_token(encoded).decode()
            if not hmac.compare_digest(signature, keyed_digest(self.secret, payload)):
                raise ValueError
            data = json.loads(payload)
            after = data.pop("after")
            if data != scope:
                raise ValueError
            timestamp = datetime.fromisoformat(after["created_at"])
            if timestamp.tzinfo is None:
                raise ValueError
            return timestamp, UUID(after["id"])
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise AppError(
                400, "invalid_cursor", "The cursor is invalid for this query."
            ) from error
