from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.exceptions.base import AppError
from app.utils.cursor import CursorCodec


def test_cursor_roundtrip_survives_deleted_anchor():
    codec = CursorCodec("secret")
    scope = codec.scope("employees", str(uuid4()), {"status": "active"})
    timestamp, identifier = datetime.now(UTC), uuid4()
    assert codec.decode(codec.encode(scope, timestamp, identifier), scope) == (
        timestamp,
        identifier,
    )


@pytest.mark.parametrize("change", ["signature", "tenant", "filters", "resource"])
def test_cursor_rejects_tampering_and_wrong_scope(change):
    codec = CursorCodec("secret")
    scope = codec.scope("employees", "tenant", {})
    token = codec.encode(scope, datetime.now(UTC), uuid4())
    if change == "signature":
        token += "x"
    else:
        scope[change] = "other"
    with pytest.raises(AppError, match="cursor"):
        codec.decode(token, scope)
