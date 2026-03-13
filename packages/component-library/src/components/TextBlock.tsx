import React from "react";

export interface TextBlockProps {
  body: string;
  title?: string;
  alignment?: "left" | "center" | "right";
  max_width?: string;
}

export function TextBlock({ body, title, alignment = "left", max_width = "720px" }: TextBlockProps) {
  return (
    <section data-component="text_block" style={{ padding: "40px 32px", maxWidth: max_width, textAlign: alignment }}>
      {title && <h2 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "12px" }}>{title}</h2>}
      <p style={{ fontSize: "1.1rem", lineHeight: 1.7, color: "#333" }}>{body}</p>
    </section>
  );
}
