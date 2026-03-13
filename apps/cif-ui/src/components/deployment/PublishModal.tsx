"use client";
import React from "react";
import { PublicationState, STATE_ACTION_LABELS, STATE_TRANSITIONS } from "@/lib/deployment-types";

interface PublishModalProps {
  assetName: string;
  assetType: string;
  versionId: string;
  currentState: PublicationState;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  error?: string | null;
}

export function PublishModal({
  assetName, assetType, versionId, currentState,
  loading, onConfirm, onCancel, error,
}: PublishModalProps) {
  const nextState = STATE_TRANSITIONS[currentState];
  const actionLabel = STATE_ACTION_LABELS[currentState];

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
      <div style={{ background: "#fff", borderRadius: "12px", padding: "32px", maxWidth: "480px", width: "100%", boxShadow: "0 20px 60px rgba(0,0,0,0.2)" }}>
        <h2 style={{ margin: "0 0 20px", fontSize: "1.25rem", fontWeight: 700 }}>{actionLabel}</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem", marginBottom: "20px" }}>
          <tbody>
            {[
              ["Asset", assetName],
              ["Type", assetType],
              ["Version ID", versionId.slice(0, 16) + "…"],
              ["Transition", `${currentState} → ${nextState}`],
            ].map(([k, v]) => (
              <tr key={k} style={{ borderBottom: "1px solid #f1f3f5" }}>
                <td style={{ padding: "8px 0", fontWeight: 600, color: "#555", width: "40%" }}>{k}</td>
                <td style={{ padding: "8px 0", color: "#333" }}>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {nextState === "published" && (
          <div style={{ padding: "10px 14px", background: "#fff3cd", border: "1px solid #ffc107", borderRadius: "6px", marginBottom: "16px", fontSize: "0.875rem", color: "#856404" }}>
            Publishing will automatically archive the currently published version.
          </div>
        )}
        {error && (
          <div style={{ padding: "10px 14px", background: "#f8d7da", border: "1px solid #f5c2c7", borderRadius: "6px", marginBottom: "16px", fontSize: "0.875rem", color: "#842029", fontWeight: 600 }}>
            {error}
          </div>
        )}
        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
          <button onClick={onCancel} disabled={loading}
            style={{ padding: "10px 20px", border: "1px solid #dee2e6", borderRadius: "6px", background: "#fff", cursor: "pointer", fontWeight: 600 }}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={loading}
            style={{ padding: "10px 20px", background: nextState === "published" ? "#198754" : "#1F3A6E", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer", opacity: loading ? 0.6 : 1 }}>
            {loading ? "Working…" : actionLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
