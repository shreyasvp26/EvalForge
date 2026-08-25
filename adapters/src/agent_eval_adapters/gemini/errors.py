"""Classify Gemini CLI failures into actionable operator messages."""

from __future__ import annotations

import json
import re


def classify_gemini_cli_failure(
    *,
    stderr: str,
    stdout: str,
    exit_code: int,
) -> str | None:
    """Return an actionable failure reason, or None when the CLI looks healthy.

    Benign stderr (YOLO notices, color warnings, ripgrep fallback) must not be
    treated as evaluation failures.
    """
    blob = f"{stderr}\n{stdout}"
    lower = blob.lower()

    if _looks_like_rate_limit(lower):
        return "Gemini API rate limit exceeded"
    if _looks_like_auth_failure(lower):
        return "Gemini authentication failed"

    extracted = _extract_result_error_message(stdout)
    if extracted:
        extracted_lower = extracted.lower()
        if _looks_like_rate_limit(extracted_lower):
            return "Gemini API rate limit exceeded"
        if _looks_like_auth_failure(extracted_lower):
            return "Gemini authentication failed"
        return f"Gemini CLI failed: {_truncate(extracted)}"

    if exit_code not in (0,):
        tail = _last_meaningful_stderr(stderr)
        if tail and _looks_like_rate_limit(tail.lower()):
            return "Gemini API rate limit exceeded"
        if tail and _looks_like_auth_failure(tail.lower()):
            return "Gemini authentication failed"
        if tail:
            return f"Gemini CLI failed (exit {exit_code}): {_truncate(tail)}"
        return f"Gemini CLI exited with code {exit_code}"

    return None


def _looks_like_rate_limit(text: str) -> bool:
    return any(
        token in text
        for token in (
            "429",
            "rate limit",
            "rate-limit",
            "quota exceeded",
            "exceeded your current quota",
            "exhausted your daily quota",
            "resource_exhausted",
        )
    )


def _looks_like_auth_failure(text: str) -> bool:
    return any(
        token in text
        for token in (
            "invalid api key",
            "api key not valid",
            "api_key_invalid",
            "unauthenticated",
            "unauthorized",
            "authentication failed",
            "missing api key",
            "provide an api key",
        )
    )


def _extract_result_error_message(stdout: str) -> str | None:
    for line in reversed(stdout.splitlines()):
        text = line.strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("type", "")).lower() not in {"result", "done", "complete"}:
            continue
        status = str(payload.get("status") or "").lower()
        if status in {"success", "completed", "ok"}:
            return None
        err = payload.get("error")
        if isinstance(err, dict):
            message = str(err.get("message") or err.get("type") or "").strip()
            if message:
                return message
        if isinstance(err, str) and err.strip():
            return err.strip()
        message = str(payload.get("message") or payload.get("result") or "").strip()
        if message:
            return message
        if status in {"error", "failure", "failed", "agent_failed"}:
            return status
    return None


def _last_meaningful_stderr(stderr: str) -> str | None:
    noise = (
        "yolo mode is enabled",
        "256-color",
        "ripgrep is not available",
        "approval mode overridden",
        "startup",
        "cannot measure phase",
    )
    for line in reversed(stderr.splitlines()):
        text = line.strip()
        if not text:
            continue
        # Strip ANSI for classification
        plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
        if any(token in plain.lower() for token in noise):
            continue
        return plain
    return None


def _truncate(message: str, limit: int = 400) -> str:
    cleaned = re.sub(r"\s+", " ", message).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."
