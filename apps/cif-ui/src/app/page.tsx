export default function DashboardPage() {
  return (
    <main style={{ padding: "64px 48px", maxWidth: "960px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "2.5rem", fontWeight: 800, marginBottom: "8px" }}>Stardance CIF</h1>
      <p style={{ fontSize: "1.1rem", color: "#555", marginBottom: "48px" }}>
        Creative Intelligence Factory — Operator Console
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "20px" }}>
        {[
          { href: "/deployments", label: "Deployment Console", desc: "Publish, deploy, and rollback asset versions", color: "#1F3A6E" },
          { href: "/surfaces", label: "Surfaces", desc: "View and manage all conversion surfaces", color: "#2E86AB" },
          { href: "/components", label: "Components", desc: "Browse the component library", color: "#2E86AB" },
          { href: "/s/phase-2-gate-test-lead-capture-a1ea", label: "Live Surface Demo", desc: "View the Phase-2 gate test surface live", color: "#198754" },
          { href: "/q/phase-4-gate-test-qds-sq2x", label: "Live QDS Demo", desc: "Run the Phase-4 gate test diagnostic", color: "#198754" },
        ].map(({ href, label, desc, color }) => (
          <a key={href} href={href} style={{
            padding: "28px", border: `2px solid ${color}20`,
            borderRadius: "12px", textDecoration: "none",
            background: "#fff", display: "block",
          }}>
            <div style={{ fontWeight: 700, fontSize: "1.1rem", color, marginBottom: "6px" }}>{label}</div>
            <div style={{ color: "#666", fontSize: "0.9rem" }}>{desc}</div>
          </a>
        ))}
      </div>
    </main>
  );
}
