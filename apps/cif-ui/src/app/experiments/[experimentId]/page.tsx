"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  fetchExperimentAnalytics,
  promoteExperimentWinner,
} from "@/lib/deployment-api";
import { getExperimentInsight, type ExperimentInsight } from "@/lib/intelligence-api";
import InsightPanel from "@/components/intelligence/InsightPanel";

type VariantResult = {
  variant_id: string;
  variant_key: string;
  is_control: boolean;
  traffic_percentage: number;
  sessions: number;
  traffic_share: number;
  goal_metric: string | null;
  goal_metric_value: number | null;
  qds_version_id: string | null;
  surface_version_id: string | null;
};

type ExperimentResult = {
  experiment_id: string;
  experiment_name: string;
  asset_id: string;
  asset_type: string;
  status: string;
  goal_metric: string | null;
  total_sessions: number;
  variant_results: VariantResult[];
  recommended_winner: string | null;
  generated_at: string;
};

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

export default function ExperimentResultsPage() {
  const params = useParams();
  const experimentId = params.experimentId as string;
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [promoting, setPromoting] = useState(false);
  const [promoteResult, setPromoteResult] = useState<string | null>(null);
  const [insight, setInsight] = useState<ExperimentInsight | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);
  const [insightError, setInsightError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchExperimentAnalytics(experimentId) as ExperimentResult;
        setResult(data);
      } catch {
        setError("Failed to load experiment results.");
      } finally {
        setLoading(false);
      }
    }
    if (experimentId) load();
  }, [experimentId]);

  if (loading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-sm text-gray-400">Loading…</div>
    </div>
  );

  if (error || !result) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-sm text-red-500">{error ?? "Not found"}</div>
    </div>
  );

  async function handlePromote(variantId: string) {
    if (!result) return;
    setPromoting(true);
    setPromoteResult(null);
    try {
      const res = await promoteExperimentWinner(
        result.experiment_id,
        variantId,
      ) as any;
      setPromoteResult(
        `Variant ${res.promoted_variant} promoted to ${res.environment}. ` +
        `Deployment ID: ${res.deployment?.id?.slice(0, 8) ?? "—"}…`
      );
      // Reload results
      const updated = await fetchExperimentAnalytics(result.experiment_id) as ExperimentResult;
      setResult(updated);
    } catch {
      setPromoteResult("Promotion failed. Check deployment console.");
    } finally {
      setPromoting(false);
    }
  }

  const winner = result.recommended_winner;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="mb-8">
          <div className="text-xs text-gray-400 uppercase tracking-widest mb-1">
            <Link href="/analytics" className="hover:text-gray-600">Analytics</Link>
            {" / "}
            <Link href="/experiments" className="hover:text-gray-600">Experiments</Link>
            {" / "}{result.experiment_id}
          </div>
          <div className="flex items-center gap-3 mt-2">
            <h1 className="text-2xl font-bold text-gray-900">
              {result.experiment_name}
            </h1>
            <StatusPill status={result.status} />
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {result.asset_type} · Asset {result.asset_id.slice(0, 8)}…
            {result.goal_metric && ` · Goal: ${result.goal_metric}`}
          </p>
        </div>

        {/* Summary metrics */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white border border-gray-200 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-gray-900">
              {result.total_sessions}
            </div>
            <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">
              Total Sessions
            </div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-gray-900">
              {result.variant_results.length}
            </div>
            <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">
              Variants
            </div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-gray-900">
              {winner ?? "—"}
            </div>
            <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">
              Leading Variant
            </div>
          </div>
        </div>

        {/* Variant comparison table */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-8">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">
              Variant Results
            </h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Variant</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Role</th>
                <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Allocation</th>
                <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Sessions</th>
                <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Traffic Share</th>
                {result.goal_metric && (
                  <th className="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase">
                    {result.goal_metric}
                  </th>
                )}
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {result.variant_results.map(v => {
                const isWinner = v.variant_key === winner;
                return (
                  <tr
                    key={v.variant_id}
                    className={isWinner ? "bg-green-50" : "hover:bg-gray-50"}
                  >
                    <td className="px-5 py-4 font-semibold text-gray-900">
                      {v.variant_key}
                      {isWinner && (
                        <span className="ml-2 text-xs text-green-700 font-normal">
                          ← leading
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-gray-500">
                      {v.is_control ? "Control" : "Variant"}
                    </td>
                    <td className="px-5 py-4 text-right text-gray-700">
                      {v.traffic_percentage}%
                    </td>
                    <td className="px-5 py-4 text-right text-gray-700">
                      {v.sessions}
                    </td>
                    <td className="px-5 py-4 text-right text-gray-700">
                      {v.traffic_share}%
                    </td>
                    {result.goal_metric && (
                      <td className="px-5 py-4 text-right text-gray-700">
                        {v.goal_metric_value !== null
                          ? v.goal_metric_value.toFixed(3)
                          : "—"}
                      </td>
                    )}
                    <td className="px-5 py-4 text-right">
                      {(v.qds_version_id || v.surface_version_id) && (
                        <span className="text-xs font-mono text-gray-400">
                          v:{(v.qds_version_id ?? v.surface_version_id ?? "").slice(0, 8)}…
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Winner recommendation */}
        {winner && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-5 mb-6">
            <div className="font-semibold text-green-900 mb-1">
              Recommended: Promote Variant {winner}
            </div>
            <p className="text-sm text-green-700 mb-3">
              Variant {winner} is leading. Promote it to production via CIF Core.
              Previous deployment will be preserved for rollback.
            </p>
            {promoteResult && (
              <div className="mb-3 p-2 bg-white border border-green-300 rounded
                text-sm text-green-800">
                {promoteResult}
              </div>
            )}
            <div className="flex gap-3">
              {result.variant_results
                .filter(v => v.variant_key === winner)
                .map(v => (
                  <button
                    key={v.variant_id}
                    onClick={() => handlePromote(v.variant_id)}
                    disabled={promoting || result.status === "complete"}
                    className="text-sm px-4 py-2 bg-green-700 text-white rounded-lg
                      hover:bg-green-800 disabled:opacity-50"
                  >
                    {promoting ? "Promoting…" : `Promote Variant ${winner} to Production`}
                  </button>
                ))}
              <Link
                href={`/deployments/${result.asset_id}?type=${result.asset_type}`}
                className="text-sm px-4 py-2 border border-green-300 text-green-700
                  rounded-lg hover:bg-green-100"
              >
                View in Deployment Console →
              </Link>
            </div>
          </div>
        )}

        <div className="text-xs text-gray-400 text-right mb-8">
          Generated: {new Date(result.generated_at).toLocaleString()}
        </div>

        {/* AI Experiment Analysis */}
        <div className="border-t border-gray-200 pt-8">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
            AI Experiment Analysis
          </h2>
          <button
            onClick={() => {
              setInsightLoading(true);
              setInsightError(null);
              getExperimentInsight(experimentId)
                .then((data) => {
                  setInsight(data);
                  setInsightLoading(false);
                })
                .catch((e) => {
                  setInsightError(e instanceof Error ? e.message : "Failed to generate insight.");
                  setInsightLoading(false);
                });
            }}
            disabled={insightLoading}
            className="text-sm px-4 py-2 border border-gray-200 rounded-lg
              hover:bg-gray-50 disabled:opacity-50 mb-4"
          >
            {insightLoading ? "Generating…" : "Generate AI Insight"}
          </button>

          {insightLoading && (
            <p className="text-xs text-gray-400 mb-4">
              Generating via local inference… this may take up to 30 seconds.
            </p>
          )}

          {(insightLoading || insight || insightError) && (
            <InsightPanel
              title="Experiment Analysis"
              insight={insight?.insight ?? ""}
              provider={insight?.provider ?? ""}
              latency_ms={insight?.latency_ms ?? 0}
              context_keys={insight?.context_keys}
              isLoading={insightLoading}
              error={insightError}
            />
          )}
        </div>
      </div>
    </div>
  );
}
