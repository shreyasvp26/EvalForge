"""Artifact preview helper tests."""

from __future__ import annotations

from agent_eval_application.artifacts.preview import (
    PREVIEW_MAX_BYTES,
    build_artifact_preview,
    is_previewable_artifact,
)


def test_preview_truncates_large_text():
    payload = b"x" * (PREVIEW_MAX_BYTES + 100)
    preview = build_artifact_preview(
        artifact_id="art-1",
        content_type="text/plain",
        size_bytes=len(payload),
        kind="log",
        payload=payload,
    )
    assert preview.previewable is True
    assert preview.truncated is True
    assert len(preview.preview or "") == PREVIEW_MAX_BYTES


def test_html_content_type_not_previewable():
    assert is_previewable_artifact(content_type="text/html", kind="log") is False
    preview = build_artifact_preview(
        artifact_id="art-2",
        content_type="text/html",
        size_bytes=10,
        kind="log",
        payload=b"<script>",
    )
    assert preview.previewable is False
    assert preview.preview is None
