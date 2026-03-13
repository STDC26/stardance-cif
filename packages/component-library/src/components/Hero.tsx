import React from "react";

export interface HeroProps {
  headline: string;
  subheadline?: string;
  primary_cta?: string;
  secondary_cta?: string;
  layout_variant?: "centered" | "left" | "right";
}

export function Hero({
  headline,
  subheadline,
  primary_cta,
  secondary_cta,
  layout_variant = "centered",
}: HeroProps) {
  const alignClass =
    layout_variant === "centered"
      ? "text-center items-center"
      : layout_variant === "right"
      ? "text-right items-end"
      : "text-left items-start";

  return (
    <section
      data-component="hero"
      style={{
        padding: "64px 32px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        background: "#f8f9fa",
      }}
      className={alignClass}
    >
      <h1 style={{ fontSize: "2.5rem", fontWeight: 700, margin: 0 }}>
        {headline}
      </h1>
      {subheadline && (
        <p style={{ fontSize: "1.25rem", color: "#555", margin: 0 }}>
          {subheadline}
        </p>
      )}
      <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
        {primary_cta && (
          <button
            style={{
              padding: "12px 24px",
              background: "#1F3A6E",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontSize: "1rem",
              cursor: "pointer",
            }}
          >
            {primary_cta}
          </button>
        )}
        {secondary_cta && (
          <button
            style={{
              padding: "12px 24px",
              background: "transparent",
              color: "#1F3A6E",
              border: "2px solid #1F3A6E",
              borderRadius: "6px",
              fontSize: "1rem",
              cursor: "pointer",
            }}
          >
            {secondary_cta}
          </button>
        )}
      </div>
    </section>
  );
}
