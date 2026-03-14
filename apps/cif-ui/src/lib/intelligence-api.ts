/**
 * CIF Intelligence API Client — Phase-6
 * Covers: Insights, Copilot, Retrieval endpoints
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://10.0.0.75:8000/api/v1";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || "cif-dev-key-001";

const headers = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

// ── Types ─────────────────────────────────────────────────────────────────

export interface ExperimentInsight {
  experiment_id: string;
  experiment_name: string;
  experiment_status: string;
  recommended_winner: string;
  total_assignments: number;
  experiment_summary: string;
  variant_comparison: Record<string, { name: string; assignments: number }>;
  insight: string;
  provider: string;
  latency_ms: number;
  context_keys: number;
}

export interface AssetInsight {
  asset_name: string;
  asset_type: string;
  asset_status: string;
  version_count: number;
  deployed_version: string;
  total_events: number;
  asset_performance_summary: string;
  insight: string;
  provider: string;
  latency_ms: number;
  context_keys: number;
}

export interface SignalInsight {
  asset_id: string;
  asset_name: string;
  total_events: number;
  signal_summary: string;
  insight: string;
  provider: string;
  latency_ms: number;
}

export interface CopilotDraftResult {
  status: "draft";
  draft: Record<string, unknown>;
  provider: string;
  latency_ms: number;
  context_keys: number;
  experiment_id?: string;
  experiment_name?: string;
  asset_name?: string;
}

export interface ExperimentRecommendations {
  status: "draft";
  draft: {
    experiments?: Array<{
      experiment_name: string;
      hypothesis: string;
      goal_metric: string;
      variants: Array<{
        variant_key: string;
        description: string;
        is_control: boolean;
      }>;
      priority: "high" | "medium" | "low";
    }>;
    rationale?: string;
    status?: string;
    [key: string]: unknown;
  };
  asset_name: string;
  provider: string;
  latency_ms: number;
  context_keys: number;
}

// ── Insight API ───────────────────────────────────────────────────────────

export async function getExperimentInsight(
  experimentId: string
): Promise<ExperimentInsight> {
  const res = await fetch(
    `${API_BASE}/insights/experiments/${experimentId}`,
    { headers }
  );
  if (!res.ok) throw new Error(`Insight fetch failed: ${res.status}`);
  return res.json();
}

export async function getAssetInsight(
  slug: string
): Promise<AssetInsight> {
  const res = await fetch(
    `${API_BASE}/insights/assets/${slug}`,
    { headers }
  );
  if (!res.ok) throw new Error(`Asset insight failed: ${res.status}`);
  return res.json();
}

export async function getSignalInsight(
  assetId: string
): Promise<SignalInsight> {
  const res = await fetch(
    `${API_BASE}/insights/signals/${assetId}`,
    { headers }
  );
  if (!res.ok) throw new Error(`Signal insight failed: ${res.status}`);
  return res.json();
}

// ── Copilot API ───────────────────────────────────────────────────────────

export async function generateSurfaceDraft(
  brief: string,
  slug?: string
): Promise<CopilotDraftResult> {
  const res = await fetch(`${API_BASE}/copilot/surface-draft`, {
    method: "POST",
    headers,
    body: JSON.stringify({ brief, slug }),
  });
  if (!res.ok) throw new Error(`Surface draft failed: ${res.status}`);
  return res.json();
}

export async function generateQDSDraft(
  brief: string,
  slug?: string
): Promise<CopilotDraftResult> {
  const res = await fetch(`${API_BASE}/copilot/qds-draft`, {
    method: "POST",
    headers,
    body: JSON.stringify({ brief, slug }),
  });
  if (!res.ok) throw new Error(`QDS draft failed: ${res.status}`);
  return res.json();
}

export async function generateVariant(
  experimentId: string,
  brief?: string
): Promise<CopilotDraftResult> {
  const res = await fetch(`${API_BASE}/copilot/variants`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      experiment_id: experimentId,
      brief,
    }),
  });
  if (!res.ok)
    throw new Error(`Variant generation failed: ${res.status}`);
  return res.json();
}

export async function recommendExperiments(
  slug: string
): Promise<ExperimentRecommendations> {
  const res = await fetch(
    `${API_BASE}/copilot/experiment-recommendations`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({ slug }),
    }
  );
  if (!res.ok)
    throw new Error(`Recommendations failed: ${res.status}`);
  return res.json();
}
