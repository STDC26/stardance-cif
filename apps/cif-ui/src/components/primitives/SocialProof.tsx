import React from "react";

export interface SocialProofProps {
  proof_type: "quotes" | "logos" | "stats" | "mixed";
  quotes?: { text: string; author: string }[];
  rating?: number;
  review_count?: number;
  logo_asset_ids?: string[];
}

export function SocialProof({ proof_type, quotes, rating, review_count, logo_asset_ids }: SocialProofProps) {
  return (
    <section data-component="social_proof" style={{ padding: "40px 32px", background: "#f8f9fa", textAlign: "center" }}>
      {rating && (
        <div style={{ marginBottom: "16px" }}>
          <span style={{ fontSize: "2rem", color: "#f4a261" }}>{"★".repeat(Math.round(rating))}{"☆".repeat(5 - Math.round(rating))}</span>
          <p style={{ margin: "4px 0 0", color: "#666" }}>{rating.toFixed(1)} from {review_count?.toLocaleString()} reviews</p>
        </div>
      )}
      {quotes && (
        <div style={{ display: "flex", gap: "24px", flexWrap: "wrap", justifyContent: "center" }}>
          {quotes.map((q, i) => (
            <blockquote key={i} style={{ maxWidth: "320px", background: "#fff", padding: "20px", borderRadius: "8px", margin: 0, boxShadow: "0 2px 8px rgba(0,0,0,0.06)", textAlign: "left" }}>
              <p style={{ fontStyle: "italic", margin: "0 0 12px" }}>"{q.text}"</p>
              <cite style={{ fontWeight: 600, fontSize: "0.875rem" }}>— {q.author}</cite>
            </blockquote>
          ))}
        </div>
      )}
      {logo_asset_ids && (
        <div style={{ display: "flex", gap: "32px", justifyContent: "center", marginTop: "24px", flexWrap: "wrap" }}>
          {logo_asset_ids.map((id, i) => (
            <div key={i} style={{ width: "80px", height: "32px", background: "#dee2e6", borderRadius: "4px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", color: "#999" }}>{id}</div>
          ))}
        </div>
      )}
    </section>
  );
}
