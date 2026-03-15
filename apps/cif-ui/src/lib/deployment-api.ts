import {
  DeployableAsset,
  AssetVersion,
  DeploymentRecord,
  PublicationState,
  DeploymentEnvironment,
} from "./deployment-types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://10.0.0.75:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "cif-dev-key-001";

const authHeaders = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders, ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      typeof err.detail === "string"
        ? err.detail
        : JSON.stringify(err.detail)
    );
  }
  return res.json();
}

// Normalize raw surface into DeployableAsset
function normalizeSurface(raw: any, version?: any, deployments?: DeploymentRecord[]): DeployableAsset {
  const activeProd = deployments?.find(
    (d) => d.environment === "production" && d.status === "active"
  );
  return {
    asset_id: raw.id ?? raw.surface_id,
    asset_name: raw.name,
    asset_type: raw.type ?? "conversion_surface",
    publication_state: version?.review_state ?? "draft",
    active_version_id: activeProd?.surface_version_id,
    deployment_target: activeProd ? "production" : undefined,
    deployment_status: activeProd ? "active" : undefined,
    updated_at: raw.created_at,
    slug: raw.slug,
  };
}

// Normalize deployment records into AssetVersion list
function normalizeVersions(deployments: DeploymentRecord[]): AssetVersion[] {
  const versionMap = new Map<string, AssetVersion>();
  const sorted = [...deployments].sort(
    (a, b) => new Date(b.deployed_at ?? 0).getTime() - new Date(a.deployed_at ?? 0).getTime()
  );

  for (const d of sorted) {
    const key = d.surface_version_id;
    if (!versionMap.has(key)) {
      const isActive = deployments.some(
        (x) => x.surface_version_id === key && x.status === "active"
      );
      const rollbackAvailable = deployments.some(
        (x) => x.surface_version_id === key && x.status === "inactive"
      );
      versionMap.set(key, {
        version_id: key,
        version_number: 0,
        publication_state: isActive ? "published" : "archived",
        created_at: d.deployed_at ?? "",
        published_at: d.deployed_at,
        deployed_at: d.deployed_at,
        is_active: isActive,
        rollback_available: rollbackAvailable,
      });
    }
  }
  return Array.from(versionMap.values());
}

export async function fetchAllAssets(): Promise<DeployableAsset[]> {
  const surfaces = await apiFetch<any[]>("/api/v1/surfaces");
  return Promise.all(
    surfaces.map(async (s) => {
      try {
        const [resolved, deps] = await Promise.all([
          apiFetch<any>(`/api/v1/surfaces/${s.id}/resolve`),
          apiFetch<DeploymentRecord[]>(`/api/v1/surfaces/${s.id}/deployments`),
        ]);
        const version = await apiFetch<any>(
          `/api/v1/surfaces/${s.id}/versions/${resolved.surface_version_id}`
        );
        return normalizeSurface({ ...s, surface_id: s.id }, version, deps);
      } catch {
        return normalizeSurface(s);
      }
    })
  );
}

export async function fetchAssetDetail(assetId: string): Promise<{
  asset: DeployableAsset;
  versions: AssetVersion[];
  deployments: DeploymentRecord[];
  currentVersionId: string;
  currentVersion: any;
}> {
  const [resolved, deployments] = await Promise.all([
    apiFetch<any>(`/api/v1/surfaces/${assetId}/resolve`),
    apiFetch<DeploymentRecord[]>(`/api/v1/surfaces/${assetId}/deployments`),
  ]);
  const currentVersion = await apiFetch<any>(
    `/api/v1/surfaces/${assetId}/versions/${resolved.surface_version_id}`
  );
  const asset = normalizeSurface(
    { id: assetId, name: resolved.name, type: "conversion_surface", slug: resolved.slug, created_at: "" },
    currentVersion,
    deployments
  );
  const versions = normalizeVersions(deployments);
  return {
    asset,
    versions,
    deployments,
    currentVersionId: resolved.surface_version_id,
    currentVersion,
  };
}

export async function transitionState(
  assetId: string,
  versionId: string,
  state: PublicationState
): Promise<void> {
  await apiFetch(`/api/v1/surfaces/${assetId}/versions/${versionId}/state`, {
    method: "PATCH",
    body: JSON.stringify({ state }),
  });
}

export async function deployVersion(
  assetId: string,
  versionId: string,
  environment: DeploymentEnvironment
): Promise<void> {
  await apiFetch(`/api/v1/surfaces/${assetId}/deploy`, {
    method: "POST",
    body: JSON.stringify({ environment, version_id: versionId }),
  });
}

export async function rollbackDeployment(
  assetId: string,
  environment: DeploymentEnvironment
): Promise<void> {
  await apiFetch(`/api/v1/surfaces/${assetId}/rollback`, {
    method: "POST",
    body: JSON.stringify({ environment }),
  });
}


// ---------------------------------------------------------------------------
// QDS API functions
// ---------------------------------------------------------------------------

function normalizeQDSDeployments(raw: any[]): DeploymentRecord[] {
  return raw.map((d) => ({
    ...d,
    surface_id: d.asset_id ?? d.surface_id,
    surface_version_id: d.version_id ?? d.surface_version_id,
  }));
}

export async function fetchAllQDSAssets(): Promise<DeployableAsset[]> {
  const assets = await apiFetch<any[]>("/api/v1/qds");
  return Promise.all(
    assets.map(async (a) => {
      try {
        const [resolved, rawDeps] = await Promise.all([
          apiFetch<any>(`/api/v1/qds/${a.id}/resolve`),
          apiFetch<any[]>(`/api/v1/qds/${a.id}/deployments`),
        ]);
        const deps = normalizeQDSDeployments(rawDeps);
        const activeProd = deps.find(
          (d) => d.environment === "production" && d.status === "active"
        );
        return {
          asset_id: a.id,
          asset_name: a.name,
          asset_type: "qds" as const,
          publication_state: resolved.review_state ?? "draft",
          active_version_id: activeProd?.surface_version_id,
          deployment_target: activeProd ? "production" : undefined,
          deployment_status: activeProd ? "active" : undefined,
          updated_at: a.created_at,
          slug: a.slug,
        } satisfies DeployableAsset;
      } catch {
        return {
          asset_id: a.id,
          asset_name: a.name,
          asset_type: "qds" as const,
          publication_state: "draft",
          updated_at: a.created_at,
          slug: a.slug,
        } satisfies DeployableAsset;
      }
    })
  );
}

export async function fetchQDSDetail(assetId: string): Promise<{
  asset: DeployableAsset;
  versions: AssetVersion[];
  deployments: DeploymentRecord[];
  currentVersionId: string;
  currentVersion: any;
}> {
  const [resolved, rawDeps] = await Promise.all([
    apiFetch<any>(`/api/v1/qds/${assetId}/resolve`),
    apiFetch<any[]>(`/api/v1/qds/${assetId}/deployments`),
  ]);
  const deployments = normalizeQDSDeployments(rawDeps);
  const currentVersion = await apiFetch<any>(
    `/api/v1/qds/${assetId}/versions/${resolved.version_id}`
  );
  const activeProd = deployments.find(
    (d) => d.environment === "production" && d.status === "active"
  );
  const asset: DeployableAsset = {
    asset_id: assetId,
    asset_name: resolved.asset_name,
    asset_type: "qds",
    publication_state: resolved.review_state ?? "draft",
    active_version_id: activeProd?.surface_version_id,
    deployment_target: activeProd ? "production" : undefined,
    deployment_status: activeProd ? "active" : undefined,
    updated_at: currentVersion?.created_at ?? "",
    slug: resolved.slug,
  };
  const versions = normalizeVersions(deployments);
  return {
    asset,
    versions,
    deployments,
    currentVersionId: resolved.version_id,
    currentVersion,
  };
}

export async function transitionQDSState(
  assetId: string,
  versionId: string,
  state: PublicationState
): Promise<void> {
  await apiFetch(`/api/v1/qds/${assetId}/versions/${versionId}/state`, {
    method: "PATCH",
    body: JSON.stringify({ state }),
  });
}

export async function deployQDSVersion(
  assetId: string,
  versionId: string,
  environment: DeploymentEnvironment
): Promise<void> {
  await apiFetch(`/api/v1/qds/${assetId}/deploy`, {
    method: "POST",
    body: JSON.stringify({ version_id: versionId, environment }),
  });
}

export async function rollbackQDSDeployment(
  assetId: string,
  environment: DeploymentEnvironment
): Promise<void> {
  await apiFetch(`/api/v1/qds/${assetId}/rollback`, {
    method: "POST",
    body: JSON.stringify({ environment }),
  });
}


// ── Analytics API ─────────────────────────────────────────────────────

export async function fetchAllAssetAnalytics(
  params: { asset_type?: string; metric_name?: string; window_type?: string } = {}
) {
  const qs = new URLSearchParams();
  if (params.asset_type) qs.set("asset_type", params.asset_type);
  if (params.metric_name) qs.set("metric_name", params.metric_name);
  if (params.window_type) qs.set("window_type", params.window_type ?? "daily");
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch(`/api/v1/analytics/assets${query}`);
}

export async function fetchAssetAnalytics(
  assetId: string,
  params: { metric_name?: string; window_type?: string } = {}
) {
  const qs = new URLSearchParams();
  if (params.metric_name) qs.set("metric_name", params.metric_name);
  qs.set("window_type", params.window_type ?? "daily");
  return apiFetch(`/api/v1/analytics/assets/${assetId}?${qs.toString()}`);
}

export async function fetchQDSAnalytics(
  params: { window_type?: string } = {}
) {
  const qs = new URLSearchParams();
  qs.set("window_type", params.window_type ?? "daily");
  return apiFetch(`/api/v1/analytics/qds?${qs.toString()}`);
}

export async function fetchSurfaceAnalytics(
  params: { window_type?: string } = {}
) {
  const qs = new URLSearchParams();
  qs.set("window_type", params.window_type ?? "daily");
  return apiFetch(`/api/v1/analytics/surfaces?${qs.toString()}`);
}

export async function fetchAllExperimentAnalytics() {
  return apiFetch("/api/v1/analytics/experiments");
}

export async function fetchExperimentAnalytics(experimentId: string) {
  return apiFetch(`/api/v1/analytics/experiments/${experimentId}`);
}

export async function fetchAllExperiments() {
  return apiFetch("/api/v1/experiments");
}

export async function fetchExperiment(experimentId: string) {
  return apiFetch(`/api/v1/experiments/${experimentId}`);
}

export async function createExperiment(body: {
  asset_id: string;
  asset_type: string;
  experiment_name: string;
  goal_metric?: string;
}) {
  return apiFetch("/api/v1/experiments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function startExperiment(experimentId: string) {
  return apiFetch(`/api/v1/experiments/${experimentId}/start`, {
    method: "POST",
  });
}

export async function pauseExperiment(experimentId: string) {
  return apiFetch(`/api/v1/experiments/${experimentId}/pause`, {
    method: "POST",
  });
}

export async function completeExperiment(experimentId: string) {
  return apiFetch(`/api/v1/experiments/${experimentId}/complete`, {
    method: "POST",
  });
}

export async function runAggregation(windowType: string = "daily") {
  return apiFetch(
    `/api/v1/analytics/run-aggregation?window_type=${windowType}`,
    { method: "POST" }
  );
}

export async function promoteExperimentWinner(
  experimentId: string,
  variantId: string,
  environment: string = "production",
  promotedBy: string = "operator"
) {
  return apiFetch(`/api/v1/experiments/${experimentId}/promote`, {
    method: "POST",
    body: JSON.stringify({
      variant_id: variantId,
      environment,
      promoted_by: promotedBy,
    }),
  });
}
