"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchAllAssetAnalytics,
  fetchAllExperimentAnalytics,
  runAggregation,
} from "@/lib/deployment-api";
import {
  getSignalInsight,
  recommendExperiments,
  type SignalInsight,
  type ExperimentRecommendations,
} from "@/lib/intelligence-api";
import InsightPanel from "@/components/intelligence/InsightPanel";

type Aggregate = {
  asset_id: string | null;
  asset_type: string;
  metric_name: string;
  metric_value: number;
  window_type: string;
  window_start: string | null;
  window_end: string | null;
  computed_at: string | null;
  experiment_id: string | null;
  variant_id: string | null;
};

type ExperimentSummary = {
  experiment_id: string;
  experiment_name: string;
  asset_id: string;
  asset_type: string;
  status: string;
  goal_metric: string | null;
  total_sessions: number;
  variants: {
    variant_key: string;
    sessions: number;
    traffic_percentage: number;
  }[];
};

function MetricBadge({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
      <div className="text-2xl font-bold text-gray-900">
        {typeof value === "number" ? (value % 1 !== 0 ? value.toFixed(3) : value) : value}
      </div>
      <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">{label}</div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    live: "bg-green-100 text-green-800",
    draft: "bg-gray-100 text-gray-600",
    paused: "bg-yellow-100 text-yellow-800",
    complete: "bg-blue-100 text-blue-800",
    archived: "bg-gray-100 text-gray-400",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

export default function AnalyticsPage() {
  const [aggregates, setAggregates] = useState<Aggregate[]>([]);
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

  // Signal Intelligence state
  const [signalAssetId, setSignalAssetId] = useState("");
  const [signalInsight, setSignalInsight] = useState<SignalInsight | null>(null);
  const [signalLoading, setSignalLoading] = useState(false);
  const [signalError, setSignalError] = useState<string | null>(null);

  // Experiment Recommendations state
  const [recSlug, setRecSlug] = useState("");
  const [recResult, setRecResult] = useState<ExperimentRecommendations | null>(null);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [aggs, exps] = await Promise.all([
        fetchAllAssetAnalytics({ window_type: "daily" }),
        fetchAllExperimentAnalytics(),
      ]);
      setAggregates(Array.isArray(aggs) ? aggs : []);
      setExperiments(Array.isArray(exps) ? exps : []);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunAggregation() {
    setRunning(true);
    setRunResult(null);
    try {
      const result = await runAggregation("daily");
      const res = result as any;
      setRunResult(`Jobs run: ${res.jobs_run} — rows written: ${res.results?.map((r: any) => r.rows_written).join(", ")}`);
      await load();
    } catch {
      setRunResult("Aggregation failed.");
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => { load(); }, []);

  // Group aggregates by asset
  const byAsset: Record<string, Aggregate[]> = {};
  for (const a of aggregates) {
    const key = a.asset_id ?? "unknown";
    if (!byAsset[key]) byAsset[key] = [];
    byAsset[key].push(a);
  }

  const liveExperiments = experiments.filter(e => e.status === "live");
  const allExperiments = experiments;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-widest mb-1">
              <Link href="/deployments" className="hover:text-gray-600">Deployments</Link>
              {" / "}Analytics
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
            <p className="text-sm text-gray-500 mt-1">
              Signal aggregates and experiment performance
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/experiments"
              className="text-sm px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              Experiment Manager →
            </Link>
            <button
              onClick={handleRunAggregation}
              disabled={running}
              className="text-sm px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
            >
              {running ? "Running…" : "Run Aggregation"}
            </button>
          </div>
        </div>

        {runResult && (
          <div className="mb-6 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
            {runResult}
          </div>
        )}

        {loading ? (
          <div className="text-sm text-gray-400">Loading…</div>
        ) : (
          <>
            {/* Live Experiments */}
            {liveExperiments.length > 0 && (
              <section className="mb-10">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
                  Live Experiments
                </h2>
                <div className="space-y-4">
                  {liveExperiments.map(exp => (
                    <div key={exp.experiment_id}
                      className="bg-white border border-gray-200 rounded-xl p-5">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <span className="font-semibold text-gray-900">
                            {exp.experiment_name}
                          </span>
                          <span className="ml-2 text-xs text-gray-400">
                            {exp.asset_type}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <StatusPill status={exp.status} />
                          <Link
                            href={`/experiments/${exp.experiment_id}`}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            View Results →
                          </Link>
                        </div>
                      </div>
                      <div className="flex gap-6 text-sm">
                        <span className="text-gray-500">
                          Sessions: <strong>{exp.total_sessions}</strong>
                        </span>
                        <span className="text-gray-500">
                          Goal: <strong>{exp.goal_metric ?? "—"}</strong>
                        </span>
                        {exp.variants.map(v => (
                          <span key={v.variant_key} className="text-gray-500">
                            {v.variant_key}: <strong>{v.sessions}</strong>
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Asset Performance */}
            <section className="mb-10">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
                Asset Performance (Daily)
              </h2>
              {Object.keys(byAsset).length === 0 ? (
                <div className="text-sm text-gray-400">
                  No aggregates found. Run aggregation to populate.
                </div>
              ) : (
                <div className="space-y-6">
                  {Object.entries(byAsset).map(([assetId, rows]) => {
                    const metricMap: Record<string, number> = {};
                    for (const r of rows) metricMap[r.metric_name] = r.metric_value;
                    return (
                      <div key={assetId}
                        className="bg-white border border-gray-200 rounded-xl p-5">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <span className="text-xs font-mono text-gray-400">
                              {assetId.slice(0, 8)}…
                            </span>
                            <span className="ml-2 text-xs text-gray-500 capitalize">
                              {rows[0]?.asset_type}
                            </span>
                          </div>
                          <Link
                            href={`/deployments/${assetId}?type=${rows[0]?.asset_type === "qds" ? "qds" : "surface"}`}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            View Asset →
                          </Link>
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                          {Object.entries(metricMap).map(([name, val]) => (
                            <MetricBadge key={name} label={name} value={val} />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* All Experiments Table */}
            <section className="mb-10">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
                All Experiments
              </h2>
              {allExperiments.length === 0 ? (
                <div className="text-sm text-gray-400">No experiments found.</div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Name</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Type</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Goal</th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Sessions</th>
                        <th className="px-4 py-3"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {allExperiments.map(exp => (
                        <tr key={exp.experiment_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">
                            {exp.experiment_name}
                          </td>
                          <td className="px-4 py-3 text-gray-500 capitalize">
                            {exp.asset_type}
                          </td>
                          <td className="px-4 py-3">
                            <StatusPill status={exp.status} />
                          </td>
                          <td className="px-4 py-3 text-gray-500">
                            {exp.goal_metric ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">
                            {exp.total_sessions}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <Link
                              href={`/experiments/${exp.experiment_id}`}
                              className="text-xs text-blue-600 hover:underline"
                            >
                              Results →
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Signal Intelligence */}
            <section className="mb-10">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
                Signal Intelligence
              </h2>
              <div className="bg-white border border-gray-200 rounded-xl p-5 mb-4">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={signalAssetId}
                    onChange={(e) => setSignalAssetId(e.target.value)}
                    placeholder="Enter asset ID (UUID)"
                    className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm
                      text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2
                      focus:ring-gray-200"
                  />
                  <button
                    onClick={() => {
                      if (!signalAssetId.trim()) return;
                      setSignalLoading(true);
                      setSignalError(null);
                      setSignalInsight(null);
                      getSignalInsight(signalAssetId)
                        .then((data) => {
                          setSignalInsight(data);
                          setSignalLoading(false);
                        })
                        .catch((e) => {
                          setSignalError(e instanceof Error ? e.message : "Failed.");
                          setSignalLoading(false);
                        });
                    }}
                    disabled={signalLoading || !signalAssetId.trim()}
                    className="text-sm px-4 py-2 bg-gray-900 text-white rounded-lg
                      hover:bg-gray-700 disabled:opacity-50"
                  >
                    {signalLoading ? "Interpreting…" : "Interpret Signals"}
                  </button>
                </div>
              </div>

              {signalError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {signalError}
                </div>
              )}

              {(signalLoading || signalInsight) && (
                <InsightPanel
                  title="Signal Interpretation"
                  insight={signalInsight?.insight ?? ""}
                  provider={signalInsight?.provider ?? ""}
                  latency_ms={signalInsight?.latency_ms ?? 0}
                  isLoading={signalLoading}
                  error={null}
                />
              )}
            </section>

            {/* Experiment Ideas */}
            <section className="mb-10">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
                Experiment Ideas
              </h2>
              <div className="bg-white border border-gray-200 rounded-xl p-5 mb-4">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={recSlug}
                    onChange={(e) => setRecSlug(e.target.value)}
                    placeholder="Enter asset slug"
                    className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm
                      text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2
                      focus:ring-gray-200"
                  />
                  <button
                    onClick={() => {
                      if (!recSlug.trim()) return;
                      setRecLoading(true);
                      setRecError(null);
                      setRecResult(null);
                      recommendExperiments(recSlug)
                        .then((data) => {
                          setRecResult(data);
                          setRecLoading(false);
                        })
                        .catch((e) => {
                          setRecError(e instanceof Error ? e.message : "Failed.");
                          setRecLoading(false);
                        });
                    }}
                    disabled={recLoading || !recSlug.trim()}
                    className="text-sm px-4 py-2 bg-gray-900 text-white rounded-lg
                      hover:bg-gray-700 disabled:opacity-50"
                  >
                    {recLoading ? "Loading…" : "Get Recommendations"}
                  </button>
                </div>
              </div>

              {recError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {recError}
                </div>
              )}

              {recLoading && (
                <div className="bg-white border border-gray-200 rounded-xl p-5">
                  <div className="animate-pulse space-y-3">
                    <div className="h-4 bg-gray-100 rounded w-1/3" />
                    <div className="h-3 bg-gray-100 rounded w-full" />
                    <div className="h-3 bg-gray-100 rounded w-5/6" />
                  </div>
                </div>
              )}

              {recResult && recResult.draft.experiments && (
                <div className="space-y-4">
                  {recResult.draft.experiments.map((exp, i) => {
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
                        <p className="text-sm text-gray-600 mb-1">
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
            </section>
          </>
        )}
      </div>
    </div>
  );
}
