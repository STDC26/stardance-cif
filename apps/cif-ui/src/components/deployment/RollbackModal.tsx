"use client";
import React from "react";
import { DeploymentRecord, DeploymentEnvironment } from "@/lib/deployment-types";

interface RollbackModalProps {
  environment: DeploymentEnvironment;
  currentDeployment: DeploymentRecord | null;
  previousDeployment: DeploymentRecord | null;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  error?: string | null;
}

export function RollbackModal({
  environment, currentDeployment, previousDeployment,
  loading, onConfirm, onCancel, error,
}: RollbackModalProps) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
      <div style={{ background: "#fff", borderRadius: "12px", padding: "32px", maxWidth: "480px", width: "100%", boxShadow: "0 20px 60px rgba(0,0,0,0.2)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: "1.25rem", fontWeight: 700 }}>
          Rollback {environment.charAt(0).toUpperCase() + environment.slice(1)}
        </h2>
        <p style={{ color: "#666", margin: "0 0 20px", fontSize: "0.9rem" }}>
          This will reactivate the previous deployment and deactivate the current version immediately.
        </p>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem", marginBottom: "20px" }}>
          <tbody>
            {[
              ["Environment", environment],
              ["Current active", currentDeployment?.deployed_at ? new Date(currentDeployment.deployed_at).toLocaleString() : "—"],
              ["Restoring to", previousDeployment?.deployed_at ? new Date(previousDeployment.deployed_at).toLocaleString() : "previous deployment"],
            ].map(([k, v]) => (
              <tr key={k} style={{ borderBottom: "1px solid #f1f3f5" }}>
                <td style={{ padding: "8px 0", fontWeight: 600, color: "#555", width: "45%" }}>{k}</td>
                <td style={{ padding: "8px 0", color: "#333" }}>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ padding: "10px 14px", background: "#f8d7da", border: "1px solid #f5c2c7", borderRadius: "6px", marginBottom: "16px", fontSize: "0.875rem", color: "#842029", fontWeight: 600 }}>
          This action takes effect immediately and cannot be automatically undone.
        </div>
        {error && (
          <div style={{ padding: "10px 14px", background: "#fff3cd", border: "1px solid #ffc107", borderRadius: "6px", marginBottom: "16px", fontSize: "0.875rem", color: "#856404" }}>
            {error}
          </div>
        )}
        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
          <button onClick={onCancel} disabled={loading}
            style={{ padding: "10px 20px", border: "1px solid #dee2e6", borderRadius: "6px", background: "#fff", cursor: "pointer", fontWeight: 600 }}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={loading}
            style={{ padding: "10px 20px", background: "#dc3545", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer", opacity: loading ? 0.6 : 1 }}>
            {loading ? "Rolling back…" : "Confirm Rollback"}
          </button>
        </div>
      </div>
    </div>
  );
}
