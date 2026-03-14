"use client";
import { useState } from "react";
import Link from "next/link";
import {
  generateSurfaceDraft,
  generateQDSDraft,
  generateVariant,
  recommendExperiments,
  type CopilotDraftResult,
  type ExperimentRecommendations,
} from "@/lib/intelligence-api";

type Tab = "surface" | "qds" | "variant" | "experiments";

function DraftBadge() {
  return (
    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-100 text-amber-800">
      DRAFT
    </span>
  );
}

export default function CopilotPage() {
  const [activeTab, setActiveTab] = useState<Tab>("surface");
  const [brief, setBrief] = useState("");
  const [slug, setSlug] = useState("");
  const [experimentId, setExperimentId] = useState("");
  const [loading, setLoading] = useState(false);
  const [draftResult, setDraftResult] = useState<CopilotDraftResult | null>(null);
  const [recResult, setRecResult] = useState<ExperimentRecommendations | null>(null);
  const [error, setError] = useState<string | null>(null);

  const tabs: { key: Tab; label: string }[] = [
    { key: "surface", label: "Surface Draft" },
    { key: "qds", label: "QDS Draft" },
    { key: "variant", label: "Variant" },
    { key: "experiments", label: "Experiment Ideas" },
  ];

  function resetResults() {
    setDraftResult(null);
    setRecResult(null);
    setError(null);
  }

  async function handleGenerate() {
    resetResults();
    setLoading(true);
    try {
      if (activeTab === "surface") {
        const res = await generateSurfaceDraft(brief, slug || undefined);
        setDraftResult(res);
      } else if (activeTab === "qds") {
        const res = await generateQDSDraft(brief, slug || undefined);
        setDraftResult(res);
      } else if (activeTab === "variant") {
        if (!experimentId.trim()) {
          setError("Experiment ID is required for variant generation.");
          setLoading(false);
          return;
        }
        const res = await generateVariant(experimentId, brief || undefined);
        setDraftResult(res);
      } else if (activeTab === "experiments") {
        if (!slug.trim()) {
          setError("Asset slug is required for experiment recommendations.");
          setLoading(false);
          return;
        }
        const res = await recommendExperiments(slug);
        setRecResult(res);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed.");
    } finally {
      setLoading(false);
    }
  }

  const tabDescriptions: Record<Tab, string> = {
    surface:
      "Generate a new conversion surface draft. Provide a brief describing what you need, and optionally a slug for context grounding.",
    qds:
      "Generate a new QDS diagnostic flow draft. Describe the troubleshooting scenario in the brief.",
    variant:
      "Generate variant suggestions for an existing experiment. Provide the experiment ID and an optional direction.",
    experiments:
      "Get AI-recommended experiments for an asset. Provide the asset slug to analyze.",
  };

  const tabPlaceholders: Record<Tab, string> = {
    surface: "Describe the surface you want to create, e.g. 'A promotional banner for a spring sale campaign'",
    qds: "Describe the diagnostic flow, e.g. 'A troubleshooting flow for network connectivity issues'",
    variant: "Describe variant direction, e.g. 'Focus on improving call-to-action visibility'",
    experiments: "",
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="mb-8">
          <div className="text-xs text-gray-400 uppercase tracking-widest mb-1">
            <Link href="/" className="hover:text-gray-600">Dashboard</Link>
            {" / "}Copilot
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Copilot</h1>
          <p className="text-sm text-gray-500 mt-1">
            AI-assisted draft generation and experiment recommendations
          </p>
        </div>

        {/* Governance notice */}
        <div className="mb-6 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          All Copilot outputs are drafts. To publish or deploy, use the{" "}
          <Link href="/deployments" className="underline hover:text-amber-900">
            Deployments console
          </Link>.
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key);
                resetResults();
              }}
              className={`text-sm px-4 py-2 -mb-px border-b-2 font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-gray-900 text-gray-900"
                  : "border-transparent text-gray-400 hover:text-gray-600"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab description */}
        <p className="text-sm text-gray-500 mb-4">
          {tabDescriptions[activeTab]}
        </p>

        {/* Input form */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
          {activeTab !== "experiments" && (
            <div className="mb-4">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Brief
              </label>
              <textarea
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder={tabPlaceholders[activeTab]}
                rows={3}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm
                  text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2
                  focus:ring-gray-200 resize-none"
              />
            </div>
          )}

          {activeTab === "variant" && (
            <div className="mb-4">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Experiment ID
              </label>
              <input
                type="text"
                value={experimentId}
                onChange={(e) => setExperimentId(e.target.value)}
                placeholder="e.g. 38623373-48ea-4a98-b02f-64a864952735"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm
                  text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2
                  focus:ring-gray-200"
              />
            </div>
          )}

          {(activeTab === "surface" || activeTab === "qds" || activeTab === "experiments") && (
            <div className="mb-4">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                {activeTab === "experiments" ? "Asset Slug" : "Slug (optional, for context)"}
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="e.g. gate-qds-version-b-dst2"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm
                  text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2
                  focus:ring-gray-200"
              />
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="text-sm px-4 py-2 bg-gray-900 text-white rounded-lg
              hover:bg-gray-700 disabled:opacity-50"
          >
            {loading ? "Generating…" : "Generate"}
          </button>

          {loading && (
            <p className="text-xs text-gray-400 mt-2">
              Generating via local inference… this may take up to 30 seconds.
            </p>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Draft result */}
        {draftResult && (
          <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-700">
                  Generated Draft
                </span>
                <DraftBadge />
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    draftResult.provider === "local"
                      ? "bg-green-100 text-green-800"
                      : "bg-blue-100 text-blue-800"
                  }`}
                >
                  {draftResult.provider}
                </span>
                <span className="text-xs text-gray-400">
                  {draftResult.latency_ms}ms
                </span>
                <span className="text-xs text-gray-400">
                  {draftResult.context_keys} context keys
                </span>
              </div>
            </div>
            <pre className="text-xs text-gray-700 bg-gray-50 border border-gray-100 rounded-lg p-4 overflow-x-auto font-mono whitespace-pre-wrap">
              {JSON.stringify(draftResult.draft, null, 2)}
            </pre>
          </div>
        )}

        {/* Experiment recommendations result */}
        {recResult && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-semibold text-gray-700">
                Experiment Recommendations for {recResult.asset_name}
              </span>
              <DraftBadge />
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  recResult.provider === "local"
                    ? "bg-green-100 text-green-800"
                    : "bg-blue-100 text-blue-800"
                }`}
              >
                {recResult.provider}
              </span>
              <span className="text-xs text-gray-400">
                {recResult.latency_ms}ms
              </span>
            </div>

            {recResult.draft.rationale && (
              <div className="bg-white border border-gray-200 rounded-xl p-5 mb-4">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Rationale
                </span>
                <p className="text-sm text-gray-700 mt-1">
                  {recResult.draft.rationale}
                </p>
              </div>
            )}

            {recResult.draft.experiments?.map((exp, i) => {
              const priorityColors: Record<string, string> = {
                high: "bg-red-100 text-red-800",
                medium: "bg-yellow-100 text-yellow-800",
                low: "bg-gray-100 text-gray-500",
              };
              return (
                <div
                  key={i}
                  className="bg-white border border-gray-200 rounded-xl p-5"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-gray-900 text-sm">
                      {exp.experiment_name}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        priorityColors[exp.priority] ?? "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {exp.priority}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">
                    {exp.hypothesis}
                  </p>
                  <div className="text-xs text-gray-400">
                    Goal: {exp.goal_metric} · {exp.variants.length} variants
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
