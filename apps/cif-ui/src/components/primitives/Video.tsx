import React from "react";

export interface VideoProps {
  asset_id: string;
  poster_asset_id?: string;
  autoplay?: boolean;
  controls?: boolean;
  caption?: string;
}

export function Video({ asset_id, caption, autoplay = false, controls = true }: VideoProps) {
  return (
    <figure data-component="video" style={{ margin: 0, padding: "24px 32px" }}>
      <div style={{ position: "relative", paddingBottom: "56.25%", background: "#1a1a2e", borderRadius: "8px", overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "0.875rem" }}>
          ▶ Video: {asset_id} {autoplay ? "(autoplay)" : ""} {controls ? "(controls)" : ""}
        </div>
      </div>
      {caption && <figcaption style={{ marginTop: "8px", fontSize: "0.875rem", color: "#666", textAlign: "center" }}>{caption}</figcaption>}
    </figure>
  );
}
