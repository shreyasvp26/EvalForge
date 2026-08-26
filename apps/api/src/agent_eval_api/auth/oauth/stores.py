"""OAuth state and one-time session exchange stores."""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class OAuthStatePayload:
    provider: str
    next_path: str
    nonce: str
    issued_at: float


@dataclass(frozen=True, slots=True)
class OAuthExchangePayload:
    user_id: str
    email: str
    display_name: str


class OAuthStateStore(Protocol):
    def create(self, *, provider: str, next_path: str) -> str: ...

    def consume(self, token: str, *, provider: str) -> OAuthStatePayload: ...


class OAuthExchangeStore(Protocol):
    def create(self, payload: OAuthExchangePayload) -> str: ...

    def consume(self, code: str) -> OAuthExchangePayload: ...


@dataclass
class InMemoryOAuthStateStore:
    ttl_seconds: int = 600
    _entries: dict[str, tuple[OAuthStatePayload, float]] = field(default_factory=dict)

    def create(self, *, provider: str, next_path: str) -> str:
        token = secrets.token_urlsafe(32)
        payload = OAuthStatePayload(
            provider=provider,
            next_path=next_path,
            nonce=secrets.token_urlsafe(16),
            issued_at=time.time(),
        )
        self._entries[token] = (payload, time.time() + self.ttl_seconds)
        return token

    def consume(self, token: str, *, provider: str) -> OAuthStatePayload:
        entry = self._entries.pop(token, None)
        if entry is None:
            raise ValueError("Invalid or expired OAuth state")
        payload, expires_at = entry
        if time.time() > expires_at:
            raise ValueError("Invalid or expired OAuth state")
        if payload.provider != provider:
            raise ValueError("OAuth state provider mismatch")
        return payload


@dataclass
class InMemoryOAuthExchangeStore:
    ttl_seconds: int = 60
    _entries: dict[str, tuple[OAuthExchangePayload, float]] = field(
        default_factory=dict
    )

    def create(self, payload: OAuthExchangePayload) -> str:
        code = secrets.token_urlsafe(32)
        self._entries[code] = (payload, time.time() + self.ttl_seconds)
        return code

    def consume(self, code: str) -> OAuthExchangePayload:
        entry = self._entries.pop(code, None)
        if entry is None:
            raise ValueError("Invalid or expired OAuth exchange code")
        payload, expires_at = entry
        if time.time() > expires_at:
            raise ValueError("Invalid or expired OAuth exchange code")
        return payload


class RedisOAuthStateStore:
    def __init__(
        self,
        redis_client: object,
        *,
        key_prefix: str = "evalforge:oauth:state",
    ) -> None:
        self._redis = redis_client
        self._prefix = key_prefix
        self._ttl_seconds = 600

    def create(self, *, provider: str, next_path: str) -> str:
        token = secrets.token_urlsafe(32)
        payload = OAuthStatePayload(
            provider=provider,
            next_path=next_path,
            nonce=secrets.token_urlsafe(16),
            issued_at=time.time(),
        )
        key = f"{self._prefix}:{token}"
        self._redis.setex(key, self._ttl_seconds, _encode(payload))
        return token

    def consume(self, token: str, *, provider: str) -> OAuthStatePayload:
        key = f"{self._prefix}:{token}"
        raw = self._redis.getdel(key) if hasattr(self._redis, "getdel") else None
        if raw is None:
            pipe = self._redis.pipeline()
            pipe.get(key)
            pipe.delete(key)
            results = pipe.execute()
            raw = results[0]
        if raw is None:
            raise ValueError("Invalid or expired OAuth state")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = _decode_state(raw)
        if payload.provider != provider:
            raise ValueError("OAuth state provider mismatch")
        return payload


class RedisOAuthExchangeStore:
    def __init__(
        self,
        redis_client: object,
        *,
        key_prefix: str = "evalforge:oauth:exchange",
        ttl_seconds: int = 60,
    ) -> None:
        self._redis = redis_client
        self._prefix = key_prefix
        self._ttl_seconds = ttl_seconds

    def create(self, payload: OAuthExchangePayload) -> str:
        code = secrets.token_urlsafe(32)
        key = f"{self._prefix}:{code}"
        self._redis.setex(key, self._ttl_seconds, _encode_exchange(payload))
        return code

    def consume(self, code: str) -> OAuthExchangePayload:
        key = f"{self._prefix}:{code}"
        raw = self._redis.getdel(key) if hasattr(self._redis, "getdel") else None
        if raw is None:
            pipe = self._redis.pipeline()
            pipe.get(key)
            pipe.delete(key)
            results = pipe.execute()
            raw = results[0]
        if raw is None:
            raise ValueError("Invalid or expired OAuth exchange code")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return _decode_exchange(raw)


def _encode(payload: OAuthStatePayload) -> str:
    return json.dumps(
        {
            "provider": payload.provider,
            "next_path": payload.next_path,
            "nonce": payload.nonce,
            "issued_at": payload.issued_at,
        }
    )


def _decode_state(raw: str) -> OAuthStatePayload:
    data: dict[str, Any] = json.loads(raw)
    return OAuthStatePayload(
        provider=str(data["provider"]),
        next_path=str(data["next_path"]),
        nonce=str(data["nonce"]),
        issued_at=float(data["issued_at"]),
    )


def _encode_exchange(payload: OAuthExchangePayload) -> str:
    return json.dumps(
        {
            "user_id": payload.user_id,
            "email": payload.email,
            "display_name": payload.display_name,
        }
    )


def _decode_exchange(raw: str) -> OAuthExchangePayload:
    data: dict[str, Any] = json.loads(raw)
    return OAuthExchangePayload(
        user_id=str(data["user_id"]),
        email=str(data["email"]),
        display_name=str(data["display_name"]),
    )
