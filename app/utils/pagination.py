from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import tuple_

from app.utils.cursor import CursorCodec


class Page[Item](BaseModel):
    items: list[Item]
    next_cursor: str | None


def page_query(query, timestamp, identifier, after, limit):
    if after:
        query = query.where(tuple_(timestamp, identifier) < tuple_(*after))
    return query.order_by(timestamp.desc(), identifier.desc()).limit(limit + 1)


def page_result(rows, limit, codec: CursorCodec, scope, render, anchor):
    selected = rows[:limit]
    cursor = None
    if len(rows) > limit:
        timestamp, identifier = anchor(selected[-1])
        cursor = codec.encode(scope, timestamp, identifier)
    return {"items": [render(row) for row in selected], "next_cursor": cursor}


def pagination(settings, resource, tenant, filters, cursor):
    codec = CursorCodec(settings.cursor_signing_key.get_secret_value())
    scope = codec.scope(resource, str(tenant), filters)
    after: tuple[datetime, UUID] | None = (
        codec.decode(cursor, scope) if cursor else None
    )
    return codec, scope, after
