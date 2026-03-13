import React from "react";

export interface ImageProps {
  asset_id: string;
  alt_text: string;
  caption?: string;
  aspect_ratio?: "16:9" | "4:3" | "1:1" | "3:2";
}

export function Image({ asset_id, alt_text, caption, aspect_ratio = "16:9" }: ImageProps) {
  const paddingMap: Record<string, string> = {
    "16:9": "56.25%", "4:3": "75%", "1:1": "100%", "3:2": "66.67%",
  };
  return (
    <figure data-component="image" style={{ margin: 0, padding: "24px 32px" }}>
      <div style={{ position: "relative", paddingBottom: paddingMap[aspect_ratio], background: "#e9ecef", borderRadius: "8px", overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#aaa", fontSize: "0.875rem" }}>
          {alt_text} (asset: {asset_id})
        </div>
      </div>
      {caption && <figcaption style={{ marginTop: "8px", fontSize: "0.875rem", color: "#666", textAlign: "center" }}>{caption}</figcaption>}
    </figure>
  );
}
