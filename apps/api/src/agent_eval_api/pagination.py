"""API-layer collection helpers — cursor page / filter / sort over DTO lists.

Application use cases still return full authorized lists. This module shapes
the HTTP envelope only (REST collection contract) without Domain changes.
Storage-efficient cursors require a future Application/repository phase.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Sequence
from typing import Any

from fastapi import HTTPException, Query
from pydantic import BaseModel

from agent_eval_api.schemas.common import CollectionResponse

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def decode_cursor(cursor: str | None) -> int:
    """Decode an opaque cursor to a zero-based offset."""
    if cursor is None or cursor == "":
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii") + b"===")
        payload = json.loads(raw.decode("utf-8"))
        offset = int(payload["o"])
    except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid cursor",
        ) from exc
    if offset < 0:
        raise HTTPException(status_code=400, detail="Invalid cursor")
    return offset


def encode_cursor(offset: int) -> str:
    payload = json.dumps({"o": offset}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _attr(item: BaseModel, name: str) -> Any:
    if hasattr(item, name):
        return getattr(item, name)
    data = item.model_dump()
    if name not in data:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown sort/filter field: {name}",
        )
    return data[name]


def filter_items[T: BaseModel](
    items: Sequence[T],
    *,
    status: str | None = None,
    q: str | None = None,
) -> list[T]:
    result = list(items)
    if status is not None:
        result = [i for i in result if hasattr(i, "status") and str(i.status) == status]
    if q is not None and q != "":
        needle = q.casefold()
        filtered: list[T] = []
        for item in result:
            name = str(getattr(item, "name", "") or "")
            description = str(getattr(item, "description", "") or "")
            if needle in name.casefold() or needle in description.casefold():
                filtered.append(item)
        result = filtered
    return result


def sort_items[T: BaseModel](items: Sequence[T], sort: str | None) -> list[T]:
    if sort is None or sort == "":
        return list(items)
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if not field:
        raise HTTPException(status_code=400, detail="Invalid sort")
    try:
        return sorted(
            items,
            key=lambda item: _attr(item, field),
            reverse=descending,
        )
    except TypeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sort by field: {field}",
        ) from exc


def paginate_items[T: BaseModel](
    items: Sequence[T],
    *,
    cursor: str | None,
    limit: int,
) -> CollectionResponse[T]:
    if limit < 1 or limit > MAX_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"limit must be between 1 and {MAX_LIMIT}",
        )
    offset = decode_cursor(cursor)
    window = list(items)[offset : offset + limit]
    next_offset = offset + len(window)
    has_more = next_offset < len(items)
    return CollectionResponse(
        items=window,
        count=len(window),
        next_cursor=encode_cursor(next_offset) if has_more else None,
        has_more=has_more,
    )


def shape_collection[T: BaseModel](
    items: Sequence[T],
    *,
    cursor: str | None = None,
    limit: int = DEFAULT_LIMIT,
    sort: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> CollectionResponse[T]:
    """Filter → sort → cursor-page an Application list into a collection envelope."""
    filtered = filter_items(items, status=status, q=q)
    ordered = sort_items(filtered, sort)
    return paginate_items(ordered, cursor=cursor, limit=limit)


class ListParams:
    """Shared FastAPI query params for collection endpoints."""

    def __init__(
        self,
        cursor: str | None = Query(
            default=None,
            description="Opaque pagination cursor",
        ),
        limit: int = Query(
            default=DEFAULT_LIMIT,
            ge=1,
            le=MAX_LIMIT,
            description="Page size",
        ),
        sort: str | None = Query(
            default=None,
            description=(
                "Sort field; prefix with '-' for descending (e.g. -created_at)"
            ),
        ),
        status: str | None = Query(default=None, description="Filter by status"),
        q: str | None = Query(default=None, description="Search name/description"),
    ) -> None:
        self.cursor = cursor
        self.limit = limit
        self.sort = sort
        self.status = status
        self.q = q

    def apply[T: BaseModel](self, items: Sequence[T]) -> CollectionResponse[T]:
        return shape_collection(
            items,
            cursor=self.cursor,
            limit=self.limit,
            sort=self.sort,
            status=self.status,
            q=self.q,
        )


# Re-export for routers that only need pagination without filter.
paginate: Callable[..., CollectionResponse[Any]] = shape_collection
