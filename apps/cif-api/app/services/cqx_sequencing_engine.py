"""
CQX Sequencing Engine v0.1

Rules-based sequencing service that takes HCTS profile, SCSS position, and
CQX intensity inputs and produces a validated, conviction-calibrated component
sequence for CHubs surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# ── Constants ─────────────────────────────────────────────────────────────────

COMPONENT_STAGE_MAP: dict[str, str] = {
    "hero": "context",
    "trust_bar": "outcome",
    "social_proof": "conviction",
    "diagnostic_entry": "direction",
    "cta": "action",
}

MUST_EXIST_STAGES: set[str] = {"action", "conviction", "direction"}
ENTRY_REQUIRED_STAGES: set[str] = {"context", "outcome"}
ALL_STAGES: set[str] = {"context", "outcome", "direction", "conviction", "action"}

INTENSITY_ORDER = ["low", "medium", "high"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _amplify(intensity: str) -> str:
    idx = INTENSITY_ORDER.index(intensity)
    return INTENSITY_ORDER[min(idx + 1, 2)]


def _moderate(intensity: str) -> str:
    idx = INTENSITY_ORDER.index(intensity)
    return INTENSITY_ORDER[max(idx - 1, 0)]


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class SequencingResult:
    component_sequence: list[dict]
    stage_coverage: dict
    conviction_expectation: str
    validation: str
    failure_reason: Optional[str]
    failure_mode: Optional[str]

    def to_dict(self) -> dict:
        return {
            "component_sequence": self.component_sequence,
            "stage_coverage": self.stage_coverage,
            "conviction_expectation": self.conviction_expectation,
            "validation": self.validation,
            "failure_reason": self.failure_reason,
            "failure_mode": self.failure_mode,
        }


# ── Engine ────────────────────────────────────────────────────────────────────

def sequence_surface(
    hcts_profile: dict,
    scss_position: str,
    cqx_intensity: str,
    components: list[dict],
) -> SequencingResult:
    """
    Produces a validated, conviction-calibrated component sequence.

    Args:
        hcts_profile:  HCTS trait scores, e.g. {"trust": 85, "empathy": 70}
        scss_position: "entry" | "mid_funnel" | "destination"
        cqx_intensity: "low" | "medium" | "high" — default intensity
        components:    list of component dicts (component_type required;
                       cqx_stage and cqx_intensity optional)

    Returns:
        SequencingResult with ordered sequence, stage coverage, conviction
        expectation, validation status, and failure detail.
    """
    scss_position = scss_position or "entry"
    cqx_intensity = cqx_intensity or "medium"
    hcts_profile = hcts_profile or {}

    # ── Step 1: assign stage + intensity to each component ────────────────
    sequenced: list[dict] = []
    for comp in components:
        comp_type = comp.get("component_type", "")
        stage = comp.get("cqx_stage") or COMPONENT_STAGE_MAP.get(comp_type, "context")
        intensity = comp.get("cqx_intensity") or cqx_intensity
        sequenced.append({**comp, "cqx_stage": stage, "cqx_intensity": intensity})

    # ── Step 2: compute stage coverage ────────────────────────────────────
    covered_stages: set[str] = {c["cqx_stage"] for c in sequenced}
    stage_coverage: dict = {s: s in covered_stages for s in sorted(ALL_STAGES)}

    # ── Step 3: required stages ───────────────────────────────────────────
    required_stages = MUST_EXIST_STAGES.copy()
    if scss_position == "entry":
        required_stages |= ENTRY_REQUIRED_STAGES

    # ── Step 4: missing stage check → immediate FAIL ──────────────────────
    missing = required_stages - covered_stages
    if missing:
        return SequencingResult(
            component_sequence=sequenced,
            stage_coverage=stage_coverage,
            conviction_expectation="low",
            validation="FAIL",
            failure_reason=f"Required stage(s) missing: {', '.join(sorted(missing))}",
            failure_mode="missing_stage",
        )

    # ── Step 5: non-fatal failure modes ───────────────────────────────────
    failure_mode: Optional[str] = None
    failure_reason: Optional[str] = None
    comp_types: set[str] = {c.get("component_type", "") for c in sequenced}
    trust_score = hcts_profile.get("trust", 100)

    # low_confidence: fewer than 3 stages covered → downgrade action intensity
    if len(covered_stages) < 3:
        failure_mode = "low_confidence"
        failure_reason = (
            f"Only {len(covered_stages)} stage(s) covered — minimum 3 required for confidence"
        )
        for c in sequenced:
            if c["cqx_stage"] == "action":
                c["cqx_intensity"] = "low"

    # conflicting_signals: trust < 60 but no trust signal components
    if (
        trust_score < 60
        and "trust_bar" not in comp_types
        and "social_proof" not in comp_types
    ):
        failure_mode = "conflicting_signals"
        failure_reason = "HCTS trust < 60 but no trust_bar or social_proof component present"
        cqx_intensity = "low"
        for c in sequenced:
            c["cqx_intensity"] = "low"

    # insufficient_conviction: conviction stage mapped but no social_proof
    if "conviction" in covered_stages and "social_proof" not in comp_types:
        if failure_mode is None:
            failure_mode = "insufficient_conviction"
            failure_reason = "Conviction stage mapped but no social_proof component present"

    # ── Step 6: HCTS weighting — adjust per-component intensity ───────────
    trust = hcts_profile.get("trust", 0)
    empathy = hcts_profile.get("empathy", 0)
    presence = hcts_profile.get("presence", 0)
    momentum = hcts_profile.get("momentum", 0)
    authenticity = hcts_profile.get("authenticity", 0)
    autonomy = hcts_profile.get("autonomy", 0)

    for c in sequenced:
        stage = c["cqx_stage"]
        intensity = c["cqx_intensity"]

        # High trust + empathy: amplify context + conviction, moderate action
        if trust >= 75 and empathy >= 75:
            if stage in ("context", "conviction"):
                intensity = _amplify(intensity)
            elif stage == "action":
                intensity = _moderate(intensity)

        # High presence + momentum: amplify conviction + action, compress context
        if presence >= 75 and momentum >= 75:
            if stage in ("conviction", "action"):
                intensity = _amplify(intensity)
            elif stage == "context":
                intensity = _moderate(intensity)

        # High authenticity: amplify outcome + context
        if authenticity >= 75:
            if stage in ("outcome", "context"):
                intensity = _amplify(intensity)

        # High autonomy: amplify direction + action, moderate conviction pressure
        if autonomy >= 75:
            if stage in ("direction", "action"):
                intensity = _amplify(intensity)
            elif stage == "conviction":
                intensity = _moderate(intensity)

        c["cqx_intensity"] = intensity

    # ── Step 7: conviction expectation ────────────────────────────────────
    ethics = hcts_profile.get("ethics", 100)
    hcts_blocks_cleared = (
        trust_score >= 60
        and ethics >= 65
        and hcts_profile.get("authenticity", 100) >= 55
    )
    conditional_covered = ENTRY_REQUIRED_STAGES <= covered_stages

    if failure_mode == "insufficient_conviction":
        conviction_expectation = "directional"
    elif not hcts_blocks_cleared or not conditional_covered:
        conviction_expectation = "directional"
    elif hcts_blocks_cleared and conditional_covered:
        conviction_expectation = "actionable"
    else:
        conviction_expectation = "low"

    return SequencingResult(
        component_sequence=sequenced,
        stage_coverage=stage_coverage,
        conviction_expectation=conviction_expectation,
        validation="PASS",
        failure_reason=failure_reason,
        failure_mode=failure_mode,
    )
