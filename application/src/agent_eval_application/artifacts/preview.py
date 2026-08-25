"""Safe artifact preview helpers."""

from __future__ import annotations

from dataclasses import dataclass

PREVIEW_MAX_BYTES = 256 * 1024

_PREVIEWABLE_KINDS = frozenset({"diff", "log", "transcript", "stdout", "stderr"})

_UNSAFE_CONTENT_TYPE_PREFIXES = (
    "text/html",
    "application/xhtml",
    "image/svg",
)


@dataclass(frozen=True, slots=True)
class ArtifactPreviewDTO:
    artifact_id: str
    content_type: str
    size_bytes: int
    preview: str | None
    truncated: bool
    previewable: bool


def is_previewable_content_type(content_type: str) -> bool:
    lowered = content_type.strip().lower()
    if not lowered:
        return False
    if lowered.startswith("text/"):
        return not any(lowered.startswith(p) for p in _UNSAFE_CONTENT_TYPE_PREFIXES)
    if lowered == "application/json":
        return True
    return False


def is_previewable_artifact(*, content_type: str, kind: str) -> bool:
    if kind.strip().lower() in _PREVIEWABLE_KINDS:
        return is_previewable_content_type(content_type)
    return is_previewable_content_type(content_type)


def build_artifact_preview(
    *,
    artifact_id: str,
    content_type: str,
    size_bytes: int,
    kind: str,
    payload: bytes,
) -> ArtifactPreviewDTO:
    previewable = is_previewable_artifact(content_type=content_type, kind=kind)
    if not previewable:
        return ArtifactPreviewDTO(
            artifact_id=artifact_id,
            content_type=content_type,
            size_bytes=size_bytes,
            preview=None,
            truncated=False,
            previewable=False,
        )

    truncated = len(payload) > PREVIEW_MAX_BYTES
    slice_bytes = payload[:PREVIEW_MAX_BYTES]
    try:
        preview_text = slice_bytes.decode("utf-8")
    except UnicodeDecodeError:
        preview_text = slice_bytes.decode("utf-8", errors="replace")

    return ArtifactPreviewDTO(
        artifact_id=artifact_id,
        content_type=content_type,
        size_bytes=size_bytes,
        preview=preview_text,
        truncated=truncated,
        previewable=True,
    )
