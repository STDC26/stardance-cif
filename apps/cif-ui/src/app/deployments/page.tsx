"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchAllAssets, fetchAllQDSAssets } from "@/lib/deployment-api";
import { DeploymentTable } from "@/components/deployment/DeploymentTable";
import { DeployableAsset } from "@/lib/deployment-types";

export default function DeploymentDashboard() {
  const [assets, setAssets] = useState<DeployableAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const [surfaces, qdsAssets] = await Promise.all([
        fetchAllAssets(),
        fetchAllQDSAssets(),
      ]);
      const merged = [...surfaces, ...qdsAssets].sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
      setAssets(merged);
    }
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ padding: "40px 48px", maxWidth: "1200px", margin: "0 auto" }}>
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "flex-start", marginBottom: "32px",
      }}>
        <div>
          <h1 style={{ fontSize: "2rem", fontWeight: 800, margin: "0 0 6px" }}>
            Deployment Console
          </h1>
          <p style={{ color: "#666", margin: 0, fontSize: "0.95rem" }}>
            Manage all CIF assets — Conversion Surfaces and Qualified Decision Systems.
          </p>
          <div className="flex gap-3 mt-3">
            <Link
              href="/analytics"
              className="text-sm px-3 py-1.5 border border-gray-200 rounded-lg
                hover:bg-gray-50 text-gray-600"
            >
              Analytics →
            </Link>
            <Link
              href="/experiments"
              className="text-sm px-3 py-1.5 border border-gray-200 rounded-lg
                hover:bg-gray-50 text-gray-600"
            >
              Experiments →
            </Link>
          </div>
        </div>
        <Link href="/" style={{
          padding: "10px 20px", border: "1px solid #1F3A6E",
          color: "#1F3A6E", borderRadius: "6px", textDecoration: "none",
          fontWeight: 600, fontSize: "0.9rem",
        }}>
          ← Dashboard
        </Link>
      </div>

      {!loading && !error && (
        <div style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
          {[
            {
              label: "Conversion Surfaces",
              count: assets.filter(a => a.asset_type !== "qds").length,
              color: "#2E86AB",
            },
            {
              label: "QDS",
              count: assets.filter(a => a.asset_type === "qds").length,
              color: "#1F3A6E",
            },
          ].map(({ label, count, color }) => (
            <div key={label} style={{
              padding: "12px 20px",
              border: `1px solid ${color}30`,
              borderRadius: "8px",
              background: `${color}08`,
            }}>
              <span style={{ fontWeight: 700, color, marginRight: "8px" }}>
                {count}
              </span>
              <span style={{ fontSize: "0.875rem", color: "#555" }}>{label}</span>
            </div>
          ))}
        </div>
      )}

      {loading && <p style={{ color: "#666" }}>Loading assets…</p>}
      {error && (
        <div style={{
          padding: "14px 18px", background: "#f8d7da",
          border: "1px solid #f5c2c7", borderRadius: "8px",
          color: "#842029", marginBottom: "24px",
        }}>
          {error}
        </div>
      )}
      {!loading && !error && <DeploymentTable assets={assets} />}
    </main>
  );
}
