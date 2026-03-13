"use client";

import { useCallback, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let sid = sessionStorage.getItem("cif_session_id");
  if (!sid) {
    sid = "sess_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem("cif_session_id", sid);
  }
  return sid;
}

export interface SignalContext {
  surface_id: string;
  surface_version_id?: string;
  experiment_id?: string;
}

export function useSignal(context: SignalContext) {
  const queue = useRef<Promise<void>>(Promise.resolve());

  const emit = useCallback(
    (eventType: string, payload: Record<string, any> = {}) => {
      const body = {
        event_type: eventType,
        surface_id: context.surface_id,
        surface_version_id: context.surface_version_id || null,
        experiment_id: context.experiment_id || null,
        session_id: getSessionId(),
        event_data: {
          ...payload,
          page_url: typeof window !== "undefined" ? window.location.href : "",
          referrer: typeof window !== "undefined" ? document.referrer : "",
          device_type: getDeviceType(),
          viewport_size: getViewportSize(),
          timestamp: new Date().toISOString(),
        },
      };

      queue.current = queue.current.then(() =>
        fetch(`${API_BASE}/api/v1/signals`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })
          .then(() => {})
          .catch((e) => console.error("Signal failed:", eventType, e))
      );
    },
    [context.surface_id, context.surface_version_id, context.experiment_id]
  );

  return { emit };
}

function getDeviceType(): string {
  if (typeof window === "undefined") return "unknown";
  const w = window.innerWidth;
  if (w < 768) return "mobile";
  if (w < 1024) return "tablet";
  return "desktop";
}

function getViewportSize(): string {
  if (typeof window === "undefined") return "unknown";
  return `${window.innerWidth}x${window.innerHeight}`;
}
