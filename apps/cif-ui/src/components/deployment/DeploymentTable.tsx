"use client";
import React from "react";
import Link from "next/link";
import { DeployableAsset, STATE_COLORS, ASSET_TYPE_LABELS } from "@/lib/deployment-types";
import { DeploymentStatusBadge } from "./DeploymentStatusBadge";

interface DeploymentTableProps {
  assets: DeployableAsset[];
}

export function DeploymentTable({ assets }: DeploymentTableProps) {
  if (assets.length === 0) {
    return <p style={{ color: "#666", padding: "24px 0" }}>No deployable assets found.</p>;
  }
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
      <thead>
        <tr style={{ borderBottom: "2px solid #dee2e6", textAlign: "left" }}>
          {["Asset", "Type", "Publication State", "Production", "Staging", "Updated", ""].map((h) => (
            <th key={h} style={{ padding: "10px 16px", fontWeight: 700, color: "#333" }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {assets.map((a) => (
          <tr key={a.asset_id} style={{ borderBottom: "1px solid #f1f3f5" }}>
            <td style={{ padding: "14px 16px" }}>
              <div style={{ fontWeight: 600 }}>{a.asset_name}</div>
              {a.slug && <div style={{ fontSize: "0.75rem", color: "#888", marginTop: "2px" }}>{a.asset_type === "qds" ? "/q/" : "/s/"}{a.slug}</div>}
            </td>
            <td style={{ padding: "14px 16px" }}>
              <DeploymentStatusBadge state={ASSET_TYPE_LABELS[a.asset_type] ?? a.asset_type} size="sm" />
            </td>
            <td style={{ padding: "14px 16px" }}>
              <DeploymentStatusBadge state={a.publication_state} />
            </td>
            <td style={{ padding: "14px 16px" }}>
              {a.deployment_target === "production" && a.deployment_status === "active"
                ? <DeploymentStatusBadge state="active" size="sm" />
                : <span style={{ color: "#aaa", fontSize: "0.85rem" }}>—</span>}
            </td>
            <td style={{ padding: "14px 16px" }}>
              <span style={{ color: "#aaa", fontSize: "0.85rem" }}>—</span>
            </td>
            <td style={{ padding: "14px 16px", color: "#888", fontSize: "0.8rem" }}>
              {a.updated_at ? new Date(a.updated_at).toLocaleDateString() : "—"}
            </td>
            <td style={{ padding: "14px 16px" }}>
              <Link href={`/deployments/${a.asset_id}?type=${a.asset_type}`}
                style={{ padding: "6px 14px", background: "#1F3A6E", color: "#fff", borderRadius: "6px", textDecoration: "none", fontSize: "0.85rem", fontWeight: 600 }}>
                Manage
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
