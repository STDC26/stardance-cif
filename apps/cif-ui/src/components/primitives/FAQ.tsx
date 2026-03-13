import React, { useState } from "react";

export interface FAQItem { question: string; answer: string; }

export interface FAQProps {
  items: FAQItem[];
  default_open_index?: number;
  style_variant?: "default" | "bordered";
}

export function FAQ({ items, default_open_index, style_variant = "default" }: FAQProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(default_open_index ?? null);

  return (
    <section data-component="faq" style={{ padding: "40px 32px", maxWidth: "720px", margin: "0 auto" }}>
      <h2 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: "24px" }}>Frequently Asked Questions</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {items.map((item, i) => (
          <div key={i} style={{ border: "1px solid #dee2e6", borderRadius: "8px", overflow: "hidden" }}>
            <button onClick={() => setOpenIndex(openIndex === i ? null : i)}
              style={{ width: "100%", padding: "16px 20px", background: openIndex === i ? "#f0f7ff" : "#fff", border: "none", textAlign: "left", fontSize: "1rem", fontWeight: 600, cursor: "pointer", display: "flex", justifyContent: "space-between" }}>
              {item.question}
              <span>{openIndex === i ? "−" : "+"}</span>
            </button>
            {openIndex === i && (
              <div style={{ padding: "16px 20px", borderTop: "1px solid #dee2e6", color: "#444", lineHeight: 1.6 }}>
                {item.answer}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
