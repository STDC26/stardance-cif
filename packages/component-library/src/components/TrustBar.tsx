import React from "react";

export interface TrustItem { label: string; icon?: string; }

export interface TrustBarProps {
  items: TrustItem[];
  icon_asset_ids?: string[];
  variant?: "light" | "dark";
}

export function TrustBar({ items, variant = "light" }: TrustBarProps) {
  const bg = variant === "dark" ? "#1F3A6E" : "#f8f9fa";
  const color = variant === "dark" ? "#fff" : "#333";

  return (
    <div data-component="trust_bar" style={{ padding: "20px 32px", background: bg, display: "flex", gap: "32px", justifyContent: "center", flexWrap: "wrap", alignItems: "center" }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: "8px", color }}>
          {item.icon && <span style={{ fontSize: "1.25rem" }}>{item.icon}</span>}
          <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
