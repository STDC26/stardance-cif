import React from "react";

export interface TestimonialProps {
  quote: string;
  author_name: string;
  author_title?: string;
  avatar_asset_id?: string;
  variant?: "card" | "inline" | "large";
}

export function Testimonial({ quote, author_name, author_title, avatar_asset_id, variant = "card" }: TestimonialProps) {
  return (
    <figure data-component="testimonial" style={{ margin: "0 auto", maxWidth: variant === "large" ? "640px" : "480px", padding: "32px", background: "#fff", borderRadius: "12px", boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }}>
      <blockquote style={{ margin: "0 0 20px", fontSize: variant === "large" ? "1.4rem" : "1.1rem", lineHeight: 1.6, fontStyle: "italic", color: "#222" }}>
        "{quote}"
      </blockquote>
      <figcaption style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "#1F3A6E", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, flexShrink: 0 }}>
          {author_name.charAt(0)}
        </div>
        <div>
          <strong style={{ display: "block" }}>{author_name}</strong>
          {author_title && <span style={{ fontSize: "0.875rem", color: "#666" }}>{author_title}</span>}
        </div>
      </figcaption>
    </figure>
  );
}
