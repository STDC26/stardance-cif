import React from "react";

interface DeploymentStatusBadgeProps {
  state: string;
  size?: "sm" | "md";
}

const BADGE_COLORS: Record<string, string> = {
  draft: "#6c757d",
  review: "#fd7e14",
  published: "#198754",
  archived: "#adb5bd",
  active: "#198754",
  inactive: "#adb5bd",
  pending: "#fd7e14",
  failed: "#dc3545",
};

export function DeploymentStatusBadge({ state, size = "md" }: DeploymentStatusBadgeProps) {
  const color = BADGE_COLORS[state] ?? "#999";
  return (
    <span style={{
      display: "inline-block",
      padding: size === "sm" ? "1px 8px" : "3px 10px",
      borderRadius: "12px",
      fontSize: size === "sm" ? "0.72rem" : "0.78rem",
      fontWeight: 700,
      background: color + "20",
      color,
      letterSpacing: "0.03em",
      textTransform: "uppercase",
      whiteSpace: "nowrap",
    }}>
      {state}
    </span>
  );
}
