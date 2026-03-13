import React from "react";

export interface OfferItem { label: string; included: boolean; }

export interface OfferStackProps {
  offer_title: string;
  items: OfferItem[];
  price: string;
  compare_at_price?: string;
  bonus_items?: string[];
  urgency_text?: string;
}

export function OfferStack({ offer_title, items, price, compare_at_price, bonus_items, urgency_text }: OfferStackProps) {
  return (
    <div data-component="offer_stack" style={{ padding: "40px 32px", maxWidth: "480px", border: "2px solid #1F3A6E", borderRadius: "12px", margin: "24px auto" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "8px" }}>{offer_title}</h2>
      <div style={{ marginBottom: "16px" }}>
        <span style={{ fontSize: "2.5rem", fontWeight: 800, color: "#1F3A6E" }}>{price}</span>
        {compare_at_price && <span style={{ marginLeft: "12px", textDecoration: "line-through", color: "#999" }}>{compare_at_price}</span>}
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: "0 0 16px", display: "flex", flexDirection: "column", gap: "8px" }}>
        {items.map((item, i) => (
          <li key={i} style={{ display: "flex", gap: "8px", color: item.included ? "#333" : "#aaa" }}>
            <span>{item.included ? "✓" : "✗"}</span>{item.label}
          </li>
        ))}
      </ul>
      {bonus_items && bonus_items.length > 0 && (
        <div style={{ background: "#f0f7ff", borderRadius: "6px", padding: "12px", marginBottom: "16px" }}>
          <strong>Bonus:</strong>
          <ul style={{ margin: "8px 0 0", paddingLeft: "16px" }}>{bonus_items.map((b, i) => <li key={i}>{b}</li>)}</ul>
        </div>
      )}
      {urgency_text && <p style={{ color: "#c0392b", fontWeight: 600, margin: 0 }}>{urgency_text}</p>}
    </div>
  );
}
