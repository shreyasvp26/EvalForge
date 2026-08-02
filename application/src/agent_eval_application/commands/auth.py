"""Auth command messages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str
