"""
T2 Phase 2 — UXC Contract Enforcement Tests
DRJ Gate: T2-PHASE2-DRJ-GATE-001
Mandate: P2-G1 — No tests → no code.

Test coverage:
  - CastPayload contract (required fields, defaults, rejection)
  - Mandatory lineage enforcement (cast_id, cycle_id, trace_id)
  - Ethics floor constant (ETHICS_FLOOR_FORGE = 45)
  - Attribution model (rendered_by / executed_by split)
  - TIS middleware (module existence + ethics gate behaviour)
  - IMS state machine (states, valid transitions, invalid transition rejection)
  - SVS operator surface (OperatorVisibility model)
  - Negative rejection paths

Steps 2-4 tests FAIL until the implementation modules exist.
"""

from __future__ import annotations

import importlib
import pytest
from pydantic import ValidationError

from app.schemas.cast_payload import CastPayload, DecisionExplanationSummary
from app.schemas.surface import ResolvedSurface
from app.registry.component_registry import ETHICS_FLOOR_FORGE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_explanation(**kwargs) -> DecisionExplanationSummary:
    defaults = dict(
        primary_reason="approved",
        pla_band="approved_test",
        confidence_sufficient=True,
        review_required=False,
    )
    return DecisionExplanationSummary(**{**defaults, **kwargs})


def _make_cast_payload(**kwargs) -> CastPayload:
    defaults = dict(
        cast_id="cast-001",
        cycle_id="cycle-001",
        trace_id="trace-001",
        pla_band="approved_test",
        decision_explanation_summary=_make_explanation(),
    )
    return CastPayload(**{**defaults, **kwargs})


def _make_resolved_surface(**kwargs) -> ResolvedSurface:
    defaults = dict(
        surface_id="surf-001",
        surface_version_id="ver-001",
        name="Test Surface",
        status="published",
        sections=[],
        components=[],
        cast_payload=_make_cast_payload(),
        cycle_id="cycle-001",
        trace_id="trace-001",
        cast_id="cast-001",
    )
    return ResolvedSurface(**{**defaults, **kwargs})


# ===========================================================================
# 1. CastPayload contract tests
# ===========================================================================

class TestCastPayloadContract:

    def test_cast_id_required(self):
        """cast_id is required — missing raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            CastPayload(
                cycle_id="c1",
                trace_id="t1",
                pla_band="approved_test",
                decision_explanation_summary=_make_explanation(),
            )
        assert "cast_id" in str(exc.value)

    def test_cycle_id_required(self):
        """cycle_id is required — missing raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            CastPayload(
                cast_id="c1",
                trace_id="t1",
                pla_band="approved_test",
                decision_explanation_summary=_make_explanation(),
            )
        assert "cycle_id" in str(exc.value)

    def test_trace_id_present(self):
        """trace_id is required and propagated to the payload."""
        p = _make_cast_payload(trace_id="trace-xyz")
        assert p.trace_id == "trace-xyz"

    def test_executed_by_defaults_to_forge(self):
        """executed_by defaults to FORGE — CIF never owns execution."""
        p = _make_cast_payload()
        assert p.executed_by == "FORGE"

    def test_schema_version_present(self):
        """schema_version must be present — contract versioning."""
        p = _make_cast_payload()
        assert p.schema_version == "1.0.0"

    def test_decision_explanation_summary_required(self):
        """decision_explanation_summary is required."""
        with pytest.raises(ValidationError):
            CastPayload(
                cast_id="c1",
                cycle_id="c1",
                trace_id="t1",
                pla_band="approved_test",
            )

    def test_valid_cast_payload_constructs(self):
        """A fully-specified CastPayload constructs without error."""
        p = _make_cast_payload()
        assert p.cast_id == "cast-001"
        assert p.cycle_id == "cycle-001"
        assert p.pla_band == "approved_test"


# ===========================================================================
# 2. Mandatory lineage enforcement tests
# ===========================================================================

class TestMandatoryLineage:

    def test_resolved_surface_requires_cast_payload(self):
        """ResolvedSurface rejects if cast_payload is absent."""
        with pytest.raises(ValidationError) as exc:
            ResolvedSurface(
                surface_id="s1",
                surface_version_id="v1",
                name="Test",
                status="published",
                sections=[],
                components=[],
                cycle_id="c1",
                trace_id="t1",
                cast_id="ca1",
            )
        assert "cast_payload" in str(exc.value)

    def test_resolved_surface_requires_cycle_id(self):
        """ResolvedSurface rejects if cycle_id is absent."""
        with pytest.raises(ValidationError) as exc:
            ResolvedSurface(
                surface_id="s1",
                surface_version_id="v1",
                name="Test",
                status="published",
                sections=[],
                components=[],
                cast_payload=_make_cast_payload(),
                trace_id="t1",
                cast_id="ca1",
            )
        assert "cycle_id" in str(exc.value)

    def test_resolved_surface_requires_cast_id(self):
        """ResolvedSurface rejects if cast_id is absent."""
        with pytest.raises(ValidationError) as exc:
            ResolvedSurface(
                surface_id="s1",
                surface_version_id="v1",
                name="Test",
                status="published",
                sections=[],
                components=[],
                cast_payload=_make_cast_payload(),
                cycle_id="c1",
                trace_id="t1",
            )
        assert "cast_id" in str(exc.value)

    def test_resolved_surface_with_full_lineage_constructs(self):
        """A fully-specified ResolvedSurface with all lineage fields constructs."""
        rs = _make_resolved_surface()
        assert rs.cycle_id == "cycle-001"
        assert rs.cast_id == "cast-001"
        assert rs.cast_payload.cycle_id == "cycle-001"


# ===========================================================================
# 3. Ethics floor tests
# ===========================================================================

class TestEthicsFloor:

    def test_ethics_floor_constant_is_45(self):
        """ETHICS_FLOOR_FORGE must be 45 — DRJ ruling UQ-3 (was 50, gap closed)."""
        assert ETHICS_FLOOR_FORGE == 45

    def test_ethics_floor_constant_is_importable(self):
        """ETHICS_FLOOR_FORGE is importable from component_registry."""
        from app.registry.component_registry import ETHICS_FLOOR_FORGE as ef
        assert isinstance(ef, int)

    def test_ethics_score_44_is_below_floor(self):
        """Score 44 is below ETHICS_FLOOR_FORGE — must be rejected."""
        assert 44 < ETHICS_FLOOR_FORGE

    def test_ethics_score_45_meets_floor(self):
        """Score 45 exactly meets ETHICS_FLOOR_FORGE — must pass."""
        assert 45 >= ETHICS_FLOOR_FORGE

    def test_ethics_score_47_meets_floor(self):
        """Score 47 passes — the 45-49 gap window is closed (was rejected at old floor 50)."""
        assert 47 >= ETHICS_FLOOR_FORGE

    def test_ethics_score_50_passes(self):
        """Score 50 passes (TIS integrity floor also satisfied)."""
        assert 50 >= ETHICS_FLOOR_FORGE

    def test_ethics_floor_not_50(self):
        """ETHICS_FLOOR_FORGE must NOT be 50 — the old gap-creating value is retired."""
        assert ETHICS_FLOOR_FORGE != 50


# ===========================================================================
# 4. Attribution model tests
# ===========================================================================

class TestAttributionModel:

    def test_rendered_by_present(self):
        """rendered_by field is present on ResolvedSurface."""
        assert "rendered_by" in ResolvedSurface.model_fields

    def test_executed_by_present(self):
        """executed_by field is present on ResolvedSurface."""
        assert "executed_by" in ResolvedSurface.model_fields

    def test_executed_by_defaults_none(self):
        """executed_by defaults to None — set by executor at runtime, not CIF."""
        rs = _make_resolved_surface()
        assert rs.executed_by is None

    def test_rendered_by_defaults_cif(self):
        """rendered_by defaults to CIF — render layer identity."""
        rs = _make_resolved_surface()
        assert rs.rendered_by == "CIF"

    def test_executed_by_can_be_set_to_forge(self):
        """executed_by can be set to FORGE at execution time."""
        rs = _make_resolved_surface(executed_by="FORGE")
        assert rs.executed_by == "FORGE"

    def test_producer_field_does_not_exist(self):
        """producer field must not exist — replaced by rendered_by/executed_by split."""
        assert "producer" not in ResolvedSurface.model_fields


# ===========================================================================
# 5. TIS Middleware tests (FAIL until Step 2 implemented)
# ===========================================================================

class TestTISMiddleware:

    def test_tis_middleware_module_exists(self):
        """app/middleware/tis.py must exist — Step 2 implementation gate."""
        spec = importlib.util.find_spec("app.middleware.tis")
        assert spec is not None, (
            "app/middleware/tis.py does not exist — implement Step 2 (TIS middleware)"
        )

    def test_tis_middleware_class_importable(self):
        """TISMiddleware class must be importable from app.middleware.tis."""
        mod = importlib.import_module("app.middleware.tis")
        assert hasattr(mod, "TISMiddleware"), (
            "TISMiddleware class not found in app/middleware/tis.py"
        )

    def test_tis_middleware_uses_ethics_floor_45(self):
        """TISMiddleware must reference ETHICS_FLOOR_FORGE (= 45), not a hardcoded value."""
        import inspect
        mod = importlib.import_module("app.middleware.tis")
        source = inspect.getsource(mod)
        assert "ETHICS_FLOOR_FORGE" in source, (
            "TISMiddleware must use ETHICS_FLOOR_FORGE constant, not a hardcoded threshold"
        )

    def test_tis_middleware_rejects_below_floor(self):
        """Ethics score 44 must be rejected (below floor of 45)."""
        from app.middleware.tis import TISMiddleware
        tis = TISMiddleware(app=None)
        assert tis._is_below_ethics_floor(44) is True

    def test_tis_middleware_passes_at_floor(self):
        """Ethics score 45 must pass (exactly at floor)."""
        from app.middleware.tis import TISMiddleware
        tis = TISMiddleware(app=None)
        assert tis._is_below_ethics_floor(45) is False

    def test_tis_middleware_passes_above_floor(self):
        """Ethics score 47 must pass (gap window is closed)."""
        from app.middleware.tis import TISMiddleware
        tis = TISMiddleware(app=None)
        assert tis._is_below_ethics_floor(47) is False


# ===========================================================================
# 6. IMS Execution State Machine tests (FAIL until Step 3 implemented)
# ===========================================================================

class TestIMSStateMachine:

    def test_execution_state_module_exists(self):
        """app/services/execution_state.py must exist — Step 3 implementation gate."""
        spec = importlib.util.find_spec("app.services.execution_state")
        assert spec is not None, (
            "app/services/execution_state.py does not exist — implement Step 3 (IMS)"
        )

    def test_execution_state_enum_importable(self):
        """ExecutionState enum must be importable."""
        mod = importlib.import_module("app.services.execution_state")
        assert hasattr(mod, "ExecutionState"), "ExecutionState enum not found"

    def test_all_required_states_present(self):
        """All required execution states must be defined."""
        from app.services.execution_state import ExecutionState
        required = {"idle", "validating", "processing", "complete", "partial_complete", "failed"}
        actual = {s.value for s in ExecutionState}
        assert required == actual, f"Missing states: {required - actual}"

    def test_valid_transition_idle_to_validating(self):
        """idle → validating is a valid transition."""
        from app.services.execution_state import ExecutionState, transition
        result = transition(ExecutionState.IDLE, ExecutionState.VALIDATING)
        assert result == ExecutionState.VALIDATING

    def test_valid_transition_validating_to_processing(self):
        """validating → processing is a valid transition."""
        from app.services.execution_state import ExecutionState, transition
        result = transition(ExecutionState.VALIDATING, ExecutionState.PROCESSING)
        assert result == ExecutionState.PROCESSING

    def test_valid_transition_processing_to_complete(self):
        """processing → complete is a valid transition."""
        from app.services.execution_state import ExecutionState, transition
        result = transition(ExecutionState.PROCESSING, ExecutionState.COMPLETE)
        assert result == ExecutionState.COMPLETE

    def test_valid_transition_processing_to_failed(self):
        """processing → failed is a valid transition."""
        from app.services.execution_state import ExecutionState, transition
        result = transition(ExecutionState.PROCESSING, ExecutionState.FAILED)
        assert result == ExecutionState.FAILED

    def test_invalid_transition_raises(self):
        """idle → complete is invalid — must raise ValueError."""
        from app.services.execution_state import ExecutionState, transition
        with pytest.raises(ValueError, match="Invalid execution state transition"):
            transition(ExecutionState.IDLE, ExecutionState.COMPLETE)

    def test_complete_is_terminal(self):
        """complete → processing is invalid — complete is terminal."""
        from app.services.execution_state import ExecutionState, transition
        with pytest.raises(ValueError):
            transition(ExecutionState.COMPLETE, ExecutionState.PROCESSING)

    def test_failed_is_terminal(self):
        """failed → validating is invalid — failed is terminal."""
        from app.services.execution_state import ExecutionState, transition
        with pytest.raises(ValueError):
            transition(ExecutionState.FAILED, ExecutionState.VALIDATING)

    def test_resolved_surface_has_execution_state_field(self):
        """ResolvedSurface must carry execution_state field."""
        assert "execution_state" in ResolvedSurface.model_fields, (
            "execution_state field not on ResolvedSurface — implement Step 3"
        )

    def test_resolved_surface_execution_state_defaults_idle(self):
        """execution_state defaults to idle on ResolvedSurface."""
        from app.services.execution_state import ExecutionState
        rs = _make_resolved_surface()
        assert rs.execution_state == ExecutionState.IDLE

    def test_resolved_surface_has_recovery_owner_field(self):
        """ResolvedSurface must carry recovery_owner field."""
        assert "recovery_owner" in ResolvedSurface.model_fields, (
            "recovery_owner field not on ResolvedSurface — implement Step 3"
        )

    def test_resolved_surface_recovery_owner_defaults_forge(self):
        """recovery_owner defaults to FORGE — FORGE owns execution recovery."""
        rs = _make_resolved_surface()
        assert rs.recovery_owner == "FORGE"


# ===========================================================================
# 7. SVS Operator Visibility Surface tests (FAIL until Step 4 implemented)
# ===========================================================================

class TestSVSOperatorSurface:

    def test_operator_visibility_model_importable(self):
        """OperatorVisibility model must exist in surface schemas."""
        from app.schemas import surface as surface_mod
        assert hasattr(surface_mod, "OperatorVisibility"), (
            "OperatorVisibility model not found in app/schemas/surface.py — implement Step 4"
        )

    def test_operator_visibility_has_pla_band(self):
        """OperatorVisibility must expose pla_band."""
        from app.schemas.surface import OperatorVisibility
        assert "pla_band" in OperatorVisibility.model_fields

    def test_operator_visibility_has_confidence_sufficient(self):
        """OperatorVisibility must expose confidence_sufficient."""
        from app.schemas.surface import OperatorVisibility
        assert "confidence_sufficient" in OperatorVisibility.model_fields

    def test_operator_visibility_has_review_required(self):
        """OperatorVisibility must expose review_required."""
        from app.schemas.surface import OperatorVisibility
        assert "review_required" in OperatorVisibility.model_fields

    def test_operator_visibility_constructs(self):
        """OperatorVisibility constructs correctly with approved fields."""
        from app.schemas.surface import OperatorVisibility
        ov = OperatorVisibility(
            pla_band="approved_test",
            confidence_sufficient=True,
            review_required=False,
        )
        assert ov.pla_band == "approved_test"
        assert ov.confidence_sufficient is True
        assert ov.review_required is False

    def test_resolved_surface_has_operator_visibility_field(self):
        """ResolvedSurface must carry operator_visibility field."""
        assert "operator_visibility" in ResolvedSurface.model_fields, (
            "operator_visibility field not on ResolvedSurface — implement Step 4"
        )

    def test_resolved_surface_operator_visibility_defaults_none(self):
        """operator_visibility defaults to None — populated at execution time."""
        rs = _make_resolved_surface()
        assert rs.operator_visibility is None

    def test_operator_visibility_no_hcts_scores(self):
        """OperatorVisibility must NOT expose raw HCTS scores (internal only)."""
        from app.schemas.surface import OperatorVisibility
        internal_fields = {"hcts_scores", "trust", "ethics", "resonance", "confidence_score"}
        exposed = set(OperatorVisibility.model_fields.keys())
        leaked = internal_fields & exposed
        assert not leaked, f"Internal scoring fields must not be on OperatorVisibility: {leaked}"


# ===========================================================================
# 8. Negative tests
# ===========================================================================

class TestNegativeRejectionPaths:

    def test_malformed_cast_payload_raises_validation_error(self):
        """Malformed CastPayload (wrong types) raises ValidationError."""
        with pytest.raises((ValidationError, TypeError)):
            CastPayload(
                cast_id=None,
                cycle_id=None,
                trace_id=None,
                pla_band=None,
                decision_explanation_summary=None,
            )

    def test_null_cast_id_rejected(self):
        """Null cast_id must be rejected — no cast_id = no execution."""
        with pytest.raises(ValidationError):
            _make_cast_payload(cast_id=None)

    def test_null_cycle_id_rejected(self):
        """Null cycle_id must be rejected — no cycle_id = no execution."""
        with pytest.raises(ValidationError):
            _make_cast_payload(cycle_id=None)

    def test_below_ethics_floor_detected(self):
        """Score below 45 must be detectable against the floor constant."""
        score = 44
        assert score < ETHICS_FLOOR_FORGE, (
            f"Score {score} must be detected as below ETHICS_FLOOR_FORGE={ETHICS_FLOOR_FORGE}"
        )

    def test_missing_rendered_by_rejected(self):
        """rendered_by cannot be None — CIF render identity is required."""
        with pytest.raises(ValidationError):
            _make_resolved_surface(rendered_by=None)
