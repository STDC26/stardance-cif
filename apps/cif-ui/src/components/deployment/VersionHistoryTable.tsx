import React from "react";
import { AssetVersion } from "@/lib/deployment-types";
import { DeploymentStatusBadge } from "./DeploymentStatusBadge";

interface VersionHistoryTableProps {
  versions: AssetVersion[];
}

export function VersionHistoryTable({ versions }: VersionHistoryTableProps) {
  if (versions.length === 0) {
    return <p style={{ color: "#666", padding: "16px 0", margin: 0 }}>No deployment history yet.</p>;
  }
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
      <thead>
        <tr style={{ borderBottom: "2px solid #dee2e6" }}>
          {["Version", "State", "Deployed At", "Published At", "Active", "Rollback"].map(h => (
            <th key={h} style={{ padding: "8px 12px", textAlign: "left", fontWeight: 700 }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {versions.map((v) => (
          <tr key={v.version_id}
            style={{ borderBottom: "1px solid #f1f3f5", background: v.is_active ? "#f0f9ff" : "#fff" }}>
            <td style={{ padding: "12px", fontFamily: "monospace", fontSize: "0.78rem", color: "#555" }}>
              {v.version_id.slice(0, 8)}…
            </td>
            <td style={{ padding: "12px" }}>
              <DeploymentStatusBadge state={v.publication_state} size="sm" />
            </td>
            <td style={{ padding: "12px", color: "#666" }}>
              {v.deployed_at ? new Date(v.deployed_at).toLocaleString() : "—"}
            </td>
            <td style={{ padding: "12px", color: "#666" }}>
              {v.published_at ? new Date(v.published_at).toLocaleString() : "—"}
            </td>
            <td style={{ padding: "12px" }}>
              {v.is_active
                ? <DeploymentStatusBadge state="active" size="sm" />
                : <span style={{ color: "#aaa" }}>—</span>}
            </td>
            <td style={{ padding: "12px" }}>
              {v.rollback_available
                ? <span style={{ fontSize: "0.8rem", color: "#dc3545", fontWeight: 700 }}>Available</span>
                : <span style={{ color: "#aaa" }}>—</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
