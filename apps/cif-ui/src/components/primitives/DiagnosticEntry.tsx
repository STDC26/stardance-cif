import React from "react";

export interface DiagnosticEntryProps {
  entry_label: string;
  entry_mode: "button" | "inline" | "modal";
  diagnostic_id: string;
  prefill_context?: Record<string, string>;
  tracking_label?: string;
  onStart?: () => void;
}

export function DiagnosticEntry({ entry_label, entry_mode, diagnostic_id, tracking_label, onStart }: DiagnosticEntryProps) {
  return (
    <div data-component="diagnostic_entry" style={{ padding: "40px 32px", textAlign: "center" }}>
      <div style={{ maxWidth: "480px", margin: "0 auto", padding: "32px", background: "#f0f7ff", borderRadius: "12px", border: "1px solid #2E86AB" }}>
        <p style={{ fontSize: "0.875rem", color: "#2E86AB", fontWeight: 600, marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Free Assessment</p>
        <h3 style={{ fontSize: "1.5rem", fontWeight: 700, margin: "0 0 20px" }}>{entry_label}</h3>
        <button
          data-diagnostic-id={diagnostic_id}
          data-tracking-label={tracking_label}
          data-entry-mode={entry_mode}
          onClick={onStart}
          style={{ padding: "14px 32px", background: "#1F3A6E", color: "#fff", border: "none", borderRadius: "6px", fontSize: "1rem", fontWeight: 600, cursor: "pointer" }}>
          Start Assessment →
        </button>
      </div>
    </div>
  );
}
