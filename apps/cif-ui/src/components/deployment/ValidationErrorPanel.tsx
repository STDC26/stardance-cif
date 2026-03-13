import React from "react";

interface ValidationErrorPanelProps {
  error: string | null;
  warnings?: string[];
  onDismiss?: () => void;
}

export function ValidationErrorPanel({ error, warnings, onDismiss }: ValidationErrorPanelProps) {
  if (!error && (!warnings || warnings.length === 0)) return null;
  return (
    <div style={{
      padding: "14px 18px",
      background: error ? "#fff3cd" : "#f8d7da",
      border: `1px solid ${error ? "#ffc107" : "#f5c2c7"}`,
      borderRadius: "8px",
      marginTop: "16px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          {error && (
            <p style={{ margin: 0, fontWeight: 700, color: "#856404" }}>
              Backend: {error}
            </p>
          )}
          {warnings?.map((w, i) => (
            <p key={i} style={{ margin: "4px 0 0", fontSize: "0.875rem", color: "#664d03" }}>{w}</p>
          ))}
        </div>
        {onDismiss && (
          <button onClick={onDismiss}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1rem", color: "#856404", padding: "0 0 0 12px" }}>
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
