"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  fetchAssetDetail,
  transitionState,
  deployVersion,
  rollbackDeployment,
  fetchQDSDetail,
  transitionQDSState,
  deployQDSVersion,
  rollbackQDSDeployment,
} from "@/lib/deployment-api";
import {
  DeployableAsset, AssetVersion, DeploymentRecord,
  PublicationState, DeploymentEnvironment,
  STATE_TRANSITIONS, STATE_ACTION_LABELS,
  ENV_ORDER,
} from "@/lib/deployment-types";
import { DeploymentStatusBadge } from "@/components/deployment/DeploymentStatusBadge";
import { VersionHistoryTable } from "@/components/deployment/VersionHistoryTable";
import { PublishModal } from "@/components/deployment/PublishModal";
import { RollbackModal } from "@/components/deployment/RollbackModal";
import { ValidationErrorPanel } from "@/components/deployment/ValidationErrorPanel";

type ModalType = "publish" | "rollback-production" | "rollback-staging" | "deploy" | null;

export default function AssetDeploymentDetail() {
  const params = useParams();
  const searchParams = useSearchParams();
  const assetId = params.assetId as string;
  const assetType = searchParams.get("type") || "conversion_surface";
  const isQDS = assetType === "qds";

  const [asset, setAsset] = useState<DeployableAsset | null>(null);
  const [versions, setVersions] = useState<AssetVersion[]>([]);
  const [deployments, setDeployments] = useState<DeploymentRecord[]>([]);
  const [currentVersionId, setCurrentVersionId] = useState<string>("");
  const [currentVersionState, setCurrentVersionState] = useState<PublicationState>("draft");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalType>(null);
  const [deployEnv, setDeployEnv] = useState<DeploymentEnvironment>("production");

  const load = useCallback(async () => {
    const data = isQDS
      ? await fetchQDSDetail(assetId)
      : await fetchAssetDetail(assetId);
    setAsset(data.asset);
    setVersions(data.versions);
    setDeployments(data.deployments);
    setCurrentVersionId(data.currentVersionId);
    setCurrentVersionState(data.currentVersion.review_state as PublicationState);
  }, [assetId, isQDS]);

  useEffect(() => {
    load().catch((e) => setPageError(e.message)).finally(() => setLoading(false));
  }, [load]);

  async function handleTransition() {
    const next = STATE_TRANSITIONS[currentVersionState];
    if (!next) return;
    setActionLoading(true);
    setActionError(null);
    try {
      if (isQDS) {
        await transitionQDSState(assetId, currentVersionId, next);
      } else {
        await transitionState(assetId, currentVersionId, next);
      }
      setModal(null);
      await load();
    } catch (e: any) {
      setActionError(e.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDeploy() {
    setActionLoading(true);
    setActionError(null);
    try {
      if (isQDS) {
        await deployQDSVersion(assetId, currentVersionId, deployEnv);
      } else {
        await deployVersion(assetId, currentVersionId, deployEnv);
      }
      setModal(null);
      await load();
    } catch (e: any) {
      setActionError(e.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRollback(env: DeploymentEnvironment) {
    setActionLoading(true);
    setActionError(null);
    try {
      if (isQDS) {
        await rollbackQDSDeployment(assetId, env);
      } else {
        await rollbackDeployment(assetId, env);
      }
      setModal(null);
      await load();
    } catch (e: any) {
      setActionError(e.message);
    } finally {
      setActionLoading(false);
    }
  }

  const canRollbackProd = deployments.filter(d => d.environment === "production" && d.status === "inactive").length > 0;
  const canRollbackStaging = deployments.filter(d => d.environment === "staging" && d.status === "inactive").length > 0;
  const nextState = STATE_TRANSITIONS[currentVersionState];
  const activeProdDep = deployments.find(d => d.environment === "production" && d.status === "active") ?? null;
  const prevProdDep = deployments.find(d => d.environment === "production" && d.status === "inactive") ?? null;
  const activeStagDep = deployments.find(d => d.environment === "staging" && d.status === "active") ?? null;
  const prevStagDep = deployments.find(d => d.environment === "staging" && d.status === "inactive") ?? null;

  const publicPath = isQDS ? `/q/${asset?.slug}` : `/s/${asset?.slug}`;

  if (loading) return <div style={{ padding: "48px" }}>Loading…</div>;
  if (pageError) return <div style={{ padding: "48px", color: "red" }}>Error: {pageError}</div>;

  return (
    <main style={{ padding: "40px 48px", maxWidth: "960px", margin: "0 auto" }}>
      {/* Modals */}
      {modal === "publish" && (
        <PublishModal
          assetName={asset?.asset_name ?? ""}
          assetType={asset?.asset_type ?? ""}
          versionId={currentVersionId}
          currentState={currentVersionState}
          loading={actionLoading}
          error={actionError}
          onConfirm={handleTransition}
          onCancel={() => { setModal(null); setActionError(null); }}
        />
      )}
      {modal === "deploy" && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "#fff", borderRadius: "12px", padding: "32px", maxWidth: "420px", width: "100%" }}>
            <h2 style={{ margin: "0 0 20px" }}>Deploy Version</h2>
            <p style={{ color: "#666", marginBottom: "16px" }}>Select deployment target:</p>
            <div style={{ display: "flex", gap: "10px", marginBottom: "24px" }}>
              {(["preview", "staging", "production"] as DeploymentEnvironment[]).map(env => (
                <button key={env} onClick={() => setDeployEnv(env)}
                  style={{ padding: "10px 18px", borderRadius: "6px", border: `2px solid ${deployEnv === env ? "#1F3A6E" : "#dee2e6"}`, background: deployEnv === env ? "#f0f4ff" : "#fff", fontWeight: deployEnv === env ? 700 : 400, cursor: "pointer", textTransform: "capitalize" }}>
                  {env}
                </button>
              ))}
            </div>
            {actionError && <p style={{ color: "red", marginBottom: "16px" }}>{actionError}</p>}
            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button onClick={() => { setModal(null); setActionError(null); }}
                style={{ padding: "10px 20px", border: "1px solid #dee2e6", borderRadius: "6px", background: "#fff", cursor: "pointer", fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={handleDeploy} disabled={actionLoading}
                style={{ padding: "10px 20px", background: "#1F3A6E", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer", opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading ? "Deploying…" : `Deploy to ${deployEnv}`}
              </button>
            </div>
          </div>
        </div>
      )}
      {modal === "rollback-production" && (
        <RollbackModal
          environment="production"
          currentDeployment={activeProdDep}
          previousDeployment={prevProdDep}
          loading={actionLoading}
          error={actionError}
          onConfirm={() => handleRollback("production")}
          onCancel={() => { setModal(null); setActionError(null); }}
        />
      )}
      {modal === "rollback-staging" && (
        <RollbackModal
          environment="staging"
          currentDeployment={activeStagDep}
          previousDeployment={prevStagDep}
          loading={actionLoading}
          error={actionError}
          onConfirm={() => handleRollback("staging")}
          onCancel={() => { setModal(null); setActionError(null); }}
        />
      )}

      {/* Header */}
      <Link href="/deployments" style={{ color: "#1F3A6E", textDecoration: "none", fontSize: "0.875rem" }}>
        ← Deployment Console
      </Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", margin: "16px 0 28px" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, margin: "0 0 8px" }}>{asset?.asset_name}</h1>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <DeploymentStatusBadge state={currentVersionState} />
            <span style={{ fontSize: "0.85rem", color: "#888" }}>
              v-{currentVersionId.slice(0, 8)}
            </span>
            {isQDS && (
              <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#1F3A6E", background: "#e8eef8", padding: "2px 8px", borderRadius: "4px" }}>
                QDS
              </span>
            )}
          </div>
          {asset?.slug && (
            <a href={publicPath} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: "0.8rem", color: "#2E86AB", marginTop: "4px", display: "inline-block" }}>
              {publicPath}
            </a>
          )}
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          {nextState && (
            <button onClick={() => { setActionError(null); setModal("publish"); }}
              style={{ padding: "10px 20px", background: nextState === "published" ? "#198754" : "#1F3A6E", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer" }}>
              {STATE_ACTION_LABELS[currentVersionState]}
            </button>
          )}
          {currentVersionState === "published" && (
            <button onClick={() => { setActionError(null); setDeployEnv("production"); setModal("deploy"); }}
              style={{ padding: "10px 20px", background: "#2E86AB", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer" }}>
              Deploy
            </button>
          )}
          {canRollbackProd && (
            <button onClick={() => { setActionError(null); setModal("rollback-production"); }}
              style={{ padding: "10px 20px", background: "#dc3545", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer" }}>
              Rollback Production
            </button>
          )}
          {canRollbackStaging && (
            <button onClick={() => { setActionError(null); setModal("rollback-staging"); }}
              style={{ padding: "10px 20px", background: "#fd7e14", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 600, cursor: "pointer" }}>
              Rollback Staging
            </button>
          )}
        </div>
      </div>

      {/* Active Deployment Status Panel */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "28px" }}>
        {ENV_ORDER.map((env) => {
          const active = deployments.find(d => d.environment === env && d.status === "active");
          return (
            <div key={env} style={{ padding: "20px", border: `2px solid ${active ? "#1F3A6E" : "#dee2e6"}`, borderRadius: "10px", background: active ? "#f0f4ff" : "#fafafa" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#888", marginBottom: "8px" }}>{env}</div>
              {active ? (
                <>
                  <div style={{ fontWeight: 700, color: "#198754" }}>● Live</div>
                  <div style={{ fontSize: "0.78rem", color: "#555", marginTop: "4px" }}>
                    {active.deployed_at ? new Date(active.deployed_at).toLocaleString() : "—"}
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "#888", marginTop: "4px" }}>by {active.deployed_by ?? "system"}</div>
                </>
              ) : (
                <div style={{ color: "#bbb", fontSize: "0.85rem" }}>No active deployment</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Version History */}
      <div style={{ padding: "24px", border: "1px solid #dee2e6", borderRadius: "8px", background: "#fff", marginBottom: "16px" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 16px" }}>Version History</h2>
        <VersionHistoryTable versions={versions} />
      </div>

      {/* Validation Error Panel */}
      <ValidationErrorPanel
        error={actionError}
        onDismiss={() => setActionError(null)}
      />
    </main>
  );
}
