export type AssetType = "conversion_surface" | "qds";

export type PublicationState = "draft" | "review" | "published" | "archived";

export type DeploymentEnvironment = "preview" | "staging" | "production";

export type DeploymentStatus = "pending" | "active" | "inactive" | "failed";

export type DeployableAsset = {
  asset_id: string;
  asset_name: string;
  asset_type: AssetType | string;
  publication_state: PublicationState;
  active_version_id?: string;
  deployment_target?: string;
  deployment_status?: string;
  updated_at: string;
  slug?: string;
};

export type AssetVersion = {
  version_id: string;
  version_number: number;
  publication_state: PublicationState;
  created_at: string;
  published_at?: string | null;
  deployed_at?: string | null;
  is_active: boolean;
  rollback_available: boolean;
};

export type DeploymentRecord = {
  id: string;
  surface_id: string;
  surface_version_id: string;
  environment: DeploymentEnvironment;
  status: DeploymentStatus;
  deployed_by: string | null;
  deployed_at: string | null;
  deactivated_at?: string | null;
};

export type DeploymentActionResult = {
  success: boolean;
  message?: string;
  blocking_issues?: string[];
  warnings?: string[];
};

export const STATE_TRANSITIONS: Record<PublicationState, PublicationState | null> = {
  draft: "review",
  review: "published",
  published: "archived",
  archived: null,
};

export const STATE_ACTION_LABELS: Record<PublicationState, string> = {
  draft: "Submit for Review",
  review: "Publish",
  published: "Archive",
  archived: "",
};

export const STATE_COLORS: Record<PublicationState, string> = {
  draft: "#6c757d",
  review: "#fd7e14",
  published: "#198754",
  archived: "#adb5bd",
};

export const ASSET_TYPE_LABELS: Record<string, string> = {
  conversion_surface: "Conversion Surface",
  lead_capture: "Conversion Surface",
  qds: "QDS",
};

export const ENV_ORDER: DeploymentEnvironment[] = [
  "production",
  "staging",
  "preview",
];
