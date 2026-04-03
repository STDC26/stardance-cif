/**
 * ContentGrid — 13th CIF primitive component (GC1 Phase 3 P3-05)
 *
 * Renders a collection of items in a CSS grid layout.
 * Supports configurable columns, gap, and style variant.
 */

import React from "react";

interface ContentGridProps {
  items: any[];
  columns?: number;
  gap?: string;
  style_variant?: string;
}

export function ContentGrid({
  items,
  columns = 3,
  gap = "1rem",
  style_variant = "default",
}: ContentGridProps) {
  const gridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: `repeat(${columns}, 1fr)`,
    gap,
  };

  const itemStyle: React.CSSProperties =
    style_variant === "card"
      ? { background: "#ffffff", border: "1px solid #e5e5e5", borderRadius: "8px", padding: "1rem" }
      : { padding: "0.5rem" };

  return (
    <div style={gridStyle}>
      {items.map((item, index) => (
        <div key={index} style={itemStyle}>
          {typeof item === "string" || typeof item === "number"
            ? item
            : item?.content ?? item?.text ?? item?.label ?? JSON.stringify(item)}
        </div>
      ))}
    </div>
  );
}

export default ContentGrid;
