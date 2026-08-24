"""Translation layer — native observations → Normalized Domain Model."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from agent_eval_domain.execution.normalized_model import (
    FileEditAction,
    MessageAction,
    NormalizedAction,
    OutputAction,
    ShellCommandAction,
    ToolCallAction,
)

from agent_eval_adapters.sdk.context import ExecutionContext
from agent_eval_adapters.sdk.exceptions import AdapterTranslationError
from agent_eval_adapters.sdk.models import (
    EmittedArtifact,
    EmittedEvent,
    EmittedProgress,
    NativeObservation,
    ObservationKind,
)


class Translator(Protocol):
    """Maps observations to NDM events / artifacts. No evaluation logic."""

    def translate(
        self,
        observation: NativeObservation,
        context: ExecutionContext,
    ) -> Sequence[EmittedEvent]: ...

    def artifacts_for(
        self,
        observation: NativeObservation,
        context: ExecutionContext,
    ) -> Sequence[EmittedArtifact]: ...

    def progress_for(
        self,
        observation: NativeObservation,
        context: ExecutionContext,
    ) -> EmittedProgress | None: ...


@dataclass(slots=True)
class DefaultTranslator:
    """Deterministic mapping from NativeObservation payloads onto NDM actions."""

    def translate(
        self,
        observation: NativeObservation,
        context: ExecutionContext,
    ) -> Sequence[EmittedEvent]:
        action = self._to_action(observation)
        if action is None:
            return ()
        event_id = self._event_id(context, observation, action)
        return (
            EmittedEvent(
                event_id=event_id,
                action=action,
                observed_at=observation.timestamp,
            ),
        )

    def artifacts_for(
        self,
        observation: NativeObservation,
        context: ExecutionContext,
    ) -> Sequence[EmittedArtifact]:
        raw = observation.raw
        raw_bytes = raw.encode("utf-8") if raw is not None else None
        payload_text = observation.payload.get("content")
        if isinstance(payload_text, str):
            content = payload_text.encode("utf-8")
        elif raw_bytes is not None:
            content = raw_bytes
        else:
            return ()

        if len(content) <= context.config.artifact_inline_max_bytes:
            return ()

        artifact_id = f"{context.run.run_id}-art-{uuid4().hex[:12]}"
        if observation.kind is ObservationKind.FILE_CHANGE:
            kind = "diff"
        elif observation.kind in {ObservationKind.STDOUT, ObservationKind.STDERR}:
            kind = "log"
        else:
            kind = "payload"
        return (
            EmittedArtifact(
                artifact_id=artifact_id,
                kind=kind,
                content=content,
                content_type="text/plain",
                metadata={"observation_kind": observation.kind.value},
            ),
        )

    def progress_for(
        self,
        observation: NativeObservation,
        context: ExecutionContext,
    ) -> EmittedProgress | None:
        del context
        if observation.kind is ObservationKind.COMPLETION:
            return EmittedProgress(message="agent completed", percent=100.0)
        if observation.kind is ObservationKind.TOOL_INVOCATION:
            name = str(observation.payload.get("tool_name", "tool"))
            return EmittedProgress(message=f"tool:{name}")
        return None

    def _to_action(self, observation: NativeObservation) -> NormalizedAction | None:
        kind = observation.kind
        payload = observation.payload

        if kind is ObservationKind.TOOL_INVOCATION:
            tool_name = str(payload.get("tool_name", "")).strip()
            if not tool_name:
                raise AdapterTranslationError(
                    "tool_invocation missing tool_name",
                    details=dict(payload),
                )
            arguments = payload.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {"value": arguments}
            result = payload.get("result_summary")
            return ToolCallAction(
                tool_name=tool_name,
                arguments=dict(arguments),
                result_summary=str(result) if result is not None else None,
            )

        if kind is ObservationKind.FILE_CHANGE:
            path = str(payload.get("path", "")).strip()
            if not path:
                raise AdapterTranslationError(
                    "file_change missing path",
                    details=dict(payload),
                )
            diff = str(payload.get("diff_summary", payload.get("content", "")))
            language = payload.get("language")
            return FileEditAction(
                path=path,
                diff_summary=diff,
                language=str(language) if language is not None else None,
            )

        if kind is ObservationKind.SHELL_COMMAND:
            command = str(payload.get("command", "")).strip()
            if not command:
                raise AdapterTranslationError(
                    "shell_command missing command",
                    details=dict(payload),
                )
            exit_code = payload.get("exit_code")
            cwd = payload.get("cwd")
            return ShellCommandAction(
                command=command,
                exit_code=int(exit_code) if exit_code is not None else None,
                cwd=str(cwd) if cwd is not None else None,
            )

        if kind is ObservationKind.STDOUT:
            return OutputAction(
                stream="stdout",
                content_summary=str(payload.get("content", observation.raw or "")),
            )

        if kind is ObservationKind.STDERR:
            return OutputAction(
                stream="stderr",
                content_summary=str(payload.get("content", observation.raw or "")),
            )

        if kind is ObservationKind.MESSAGE:
            role = str(payload.get("role", "assistant")).strip() or "assistant"
            return MessageAction(
                role=role,
                content_summary=str(payload.get("content", "")),
            )

        if kind is ObservationKind.COMPLETION:
            return MessageAction(
                role="system",
                content_summary=str(payload.get("status", "completed")),
            )

        if kind is ObservationKind.ERROR:
            return MessageAction(
                role="system",
                content_summary=str(payload.get("message", "error")),
            )

        raise AdapterTranslationError(
            f"Unsupported observation kind: {kind!r}",
            details={"kind": str(kind)},
        )

    def _event_id(
        self,
        context: ExecutionContext,
        observation: NativeObservation,
        action: NormalizedAction,
    ) -> str:
        del observation, action
        # Must fit DB ``String(64)`` PKs. Full run_id + kind + timestamp overflows.
        return f"evt-{context.run.run_id[:8]}-{uuid4().hex[:16]}"


def observation_now(
    kind: ObservationKind,
    *,
    payload: dict[str, object] | None = None,
    raw: str | None = None,
    timestamp: datetime | None = None,
) -> NativeObservation:
    return NativeObservation(
        kind=kind,
        timestamp=timestamp or datetime.now(UTC),
        payload=payload or {},
        raw=raw,
    )
