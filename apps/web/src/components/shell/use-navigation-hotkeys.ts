"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return target.closest("[role='textbox'], [contenteditable='true']") !== null;
}

export interface NavigationHotkeysOptions {
  onOpenCommand: () => void;
  onOpenShortcuts: () => void;
  onCloseOverlays: () => void;
  enabled?: boolean;
}

/**
 * Global navigation chords and helpers. Ignores events while typing in fields.
 */
export function useNavigationHotkeys({
  onOpenCommand,
  onOpenShortcuts,
  onCloseOverlays,
  enabled = true,
}: NavigationHotkeysOptions) {
  const router = useRouter();
  const chordRef = useRef<string | null>(null);
  const chordTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const clearChord = () => {
      chordRef.current = null;
      if (chordTimer.current !== null) {
        window.clearTimeout(chordTimer.current);
        chordTimer.current = null;
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (isTypingTarget(event.target)) return;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        clearChord();
        onOpenCommand();
        return;
      }

      if (event.key === "Escape") {
        onCloseOverlays();
        clearChord();
        return;
      }

      if (event.key === "?" && !event.metaKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        clearChord();
        onOpenShortcuts();
        return;
      }

      if (event.metaKey || event.ctrlKey || event.altKey) return;

      const key = event.key.toLowerCase();

      if (chordRef.current === "g") {
        event.preventDefault();
        if (key === "h") router.push("/");
        if (key === "p") router.push("/projects");
        if (key === "r") router.push("/runs");
        if (key === "a") router.push("/agents");
        if (key === "g") router.push("/graders");
        clearChord();
        return;
      }

      if (key === "g") {
        chordRef.current = "g";
        if (chordTimer.current !== null) window.clearTimeout(chordTimer.current);
        chordTimer.current = window.setTimeout(() => {
          clearChord();
        }, 800);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      clearChord();
    };
  }, [enabled, onCloseOverlays, onOpenCommand, onOpenShortcuts, router]);
}
