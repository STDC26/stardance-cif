"use client";
import { useState } from "react";
import Link from "next/link";
import { getAssetInsight, type AssetInsight } from "@/lib/intelligence-api";
import InsightPanel from "@/components/intelligence/InsightPanel";

export default function DraftsPage() {
  const [slug, setSlug] = useState("");
  const [insight, setInsight] = useState<AssetInsight | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGetInsight() {
    if (!slug.trim()) return;
    setLoading(true);
    setError(null);
    setInsight(null);
    try {
      const data = await getAssetInsight(slug);
      setInsight(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load insight.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="mb-8">
          <div className="text-xs text-gray-400 uppercase tracking-widest mb-1">
            <Link href="/" className="hover:text-gray-600">Dashboard</Link>
            {" / "}Drafts
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Drafts</h1>
          <p className="text-sm text-gray-500 mt-1">
            AI-generated asset intelligence and quick actions
          </p>
        </div>

        {/* Governance notice */}
        <div className="mb-6 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          AI-generated assets are drafts. Use{" "}
          <Link href="/deployments" className="underline hover:text-amber-900">
            Deployments
          </Link>{" "}
          to publish and deploy.
        </div>

        {/* Section 1 — Asset Intelligence */}
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
            Asset Performance
          </h2>
          <div className="bg-white border border-gray-200 rounded-xl p-5 mb-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="Enter asset slug, e.g. gate-qds-version-b-dst2"
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm
                  text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2
                  focus:ring-gray-200"
              />
              <button
                onClick={handleGetInsight}
                disabled={loading || !slug.trim()}
                className="text-sm px-4 py-2 bg-gray-900 text-white rounded-lg
                  hover:bg-gray-700 disabled:opacity-50"
              >
                {loading ? "Loading…" : "Get AI Summary"}
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {(loading || insight) && (
            <InsightPanel
              title="Asset Performance Summary"
              insight={insight?.insight ?? ""}
              provider={insight?.provider ?? ""}
              latency_ms={insight?.latency_ms ?? 0}
              context_keys={insight?.context_keys}
              isLoading={loading}
              error={null}
            />
          )}
        </section>

        {/* Section 2 — Quick Actions */}
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
            Generate with Copilot
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <Link
              href="/copilot"
              className="bg-white border border-gray-200 rounded-xl p-5 block
                hover:border-gray-300 hover:shadow-sm transition-all"
            >
              <div className="font-semibold text-gray-900 text-sm mb-1">
                Generate Surface Draft
              </div>
              <div className="text-xs text-gray-500">
                Create a new conversion surface draft using AI assistance
              </div>
            </Link>
            <Link
              href="/copilot"
              className="bg-white border border-gray-200 rounded-xl p-5 block
                hover:border-gray-300 hover:shadow-sm transition-all"
            >
              <div className="font-semibold text-gray-900 text-sm mb-1">
                Generate Experiment Ideas
              </div>
              <div className="text-xs text-gray-500">
                Get AI-recommended experiments to optimize asset performance
              </div>
            </Link>
          </div>
        </section>

        {/* Footer note */}
        <div className="text-xs text-gray-400">
          Drafts are reviewed here. Lifecycle actions happen in{" "}
          <Link href="/deployments" className="text-blue-600 hover:underline">
            Deployments
          </Link>.
        </div>
      </div>
    </div>
  );
}
