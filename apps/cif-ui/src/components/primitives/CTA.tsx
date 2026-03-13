import React from "react";

export interface CTAProps {
  label: string;
  action_type: "link" | "scroll" | "modal" | "submit";
  action_target: string;
  style_variant?: "primary" | "secondary" | "ghost";
  tracking_label?: string;
  onClick?: () => void;
}

export function CTA({
  label,
  action_type,
  action_target,
  style_variant = "primary",
  tracking_label,
  onClick,
}: CTAProps) {
  const styles: Record<string, React.CSSProperties> = {
    primary: {
      padding: "14px 28px",
      background: "#1F3A6E",
      color: "#fff",
      border: "none",
      borderRadius: "6px",
      fontSize: "1rem",
      fontWeight: 600,
      cursor: "pointer",
    },
    secondary: {
      padding: "14px 28px",
      background: "#2E86AB",
      color: "#fff",
      border: "none",
      borderRadius: "6px",
      fontSize: "1rem",
      fontWeight: 600,
      cursor: "pointer",
    },
    ghost: {
      padding: "14px 28px",
      background: "transparent",
      color: "#1F3A6E",
      border: "2px solid #1F3A6E",
      borderRadius: "6px",
      fontSize: "1rem",
      fontWeight: 600,
      cursor: "pointer",
    },
  };

  return (
    <button
      data-component="cta"
      data-tracking-label={tracking_label}
      data-action-type={action_type}
      data-action-target={action_target}
      style={styles[style_variant]}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
