"use client";

import { Button, Text } from "@agent-eval/ui";
import { useEffect, useState } from "react";

/**
 * Lightweight offline banner. Does not block the app — only surfaces connectivity loss.
 */
export function OfflineBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    function sync() {
      setOffline(!window.navigator.onLine);
    }
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="status"
      className="border-b border-warning/40 bg-warning-muted px-4 py-2 text-warning"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2">
        <Text as="span" variant="body" className="text-inherit">
          You appear to be offline. Changes and API calls may fail until connectivity returns.
        </Text>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => {
            window.location.reload();
          }}
        >
          Retry
        </Button>
      </div>
    </div>
  );
}
