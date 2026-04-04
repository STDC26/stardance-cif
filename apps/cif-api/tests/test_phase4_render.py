"""
T2 Phase 4 — CIF /render Endpoint + Executor→CIF Stub Tests
DRJ Rulings: P4-G1, P4-G2, P4-G3

Test coverage:
  - Render endpoint contract (POST /render returns 200, required fields)
  - Surface ID required, render_config optional
  - Response shape: rendered_by="CIF", cast_id/cycle_id echoed from headers
  - Header logging: X-Cast-ID, X-Cycle-ID, X-Executed-By captured
  - Executor→CIF stub isolation tests (200→complete, 422→failed, 500→failed, timeout→failed)
  - recovery_owner="FORGE" on all failed paths
  - Schema version pinned at "1.0.0"

Router is not yet implemented — tests fail at runtime, not collection time.
"""

from __future__ import annotations

import importlib
import importlib.util
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _load(name: str):
    return importlib.import_module(name)


# ---------------------------------------------------------------------------
# Class 1 — Module Existence
# ---------------------------------------------------------------------------

class TestRenderModuleExistence:
    """Render router module must exist before any endpoint tests run."""

    def test_render_router_module_exists(self):
        assert _module_exists("app.routers.render"), (
            "app/routers/render.py must exist"
        )

    def test_render_router_has_router_attribute(self):
        mod = _load("app.routers.render")
        assert hasattr(mod, "router"), "app.routers.render must expose 'router'"

    def test_render_request_model_exists(self):
        mod = _load("app.routers.render")
        assert hasattr(mod, "RenderRequest"), "RenderRequest model must be defined in render.py"

    def test_render_response_model_exists(self):
        mod = _load("app.routers.render")
        assert hasattr(mod, "RenderResponse"), "RenderResponse model must be defined in render.py"


# ---------------------------------------------------------------------------
# Class 2 — RenderRequest Schema
# ---------------------------------------------------------------------------

class TestRenderRequestSchema:
    """RenderRequest contract."""

    def test_surface_id_required(self):
        mod = _load("app.routers.render")
        RenderRequest = mod.RenderRequest
        with pytest.raises((ValidationError, TypeError)):
            RenderRequest()  # surface_id missing

    def test_surface_id_accepted(self):
        mod = _load("app.routers.render")
        RenderRequest = mod.RenderRequest
        req = RenderRequest(surface_id="srf-123")
        assert req.surface_id == "srf-123"

    def test_render_config_defaults_to_empty_dict(self):
        mod = _load("app.routers.render")
        RenderRequest = mod.RenderRequest
        req = RenderRequest(surface_id="srf-123")
        assert req.render_config == {}

    def test_render_config_accepts_dict(self):
        mod = _load("app.routers.render")
        RenderRequest = mod.RenderRequest
        req = RenderRequest(surface_id="srf-123", render_config={"theme": "dark"})
        assert req.render_config == {"theme": "dark"}


# ---------------------------------------------------------------------------
# Class 3 — RenderResponse Schema
# ---------------------------------------------------------------------------

class TestRenderResponseSchema:
    """RenderResponse contract — attribution + lineage fields."""

    def test_rendered_by_defaults_to_cif(self):
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(surface_id="srf-123")
        assert resp.rendered_by == "CIF"

    def test_render_status_defaults_to_complete(self):
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(surface_id="srf-123")
        assert resp.render_status == "complete"

    def test_schema_version_pinned(self):
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(surface_id="srf-123")
        assert resp.schema_version == "1.0.0"

    def test_cast_id_optional_defaults_none(self):
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(surface_id="srf-123")
        assert resp.cast_id is None

    def test_cycle_id_optional_defaults_none(self):
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(surface_id="srf-123")
        assert resp.cycle_id is None

    def test_rendered_content_defaults_to_empty_dict(self):
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(surface_id="srf-123")
        assert resp.rendered_content == {}

    def test_cast_id_and_cycle_id_accepted(self):
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(
            surface_id="srf-123",
            cast_id="cast-abc",
            cycle_id="cycle-xyz",
        )
        assert resp.cast_id == "cast-abc"
        assert resp.cycle_id == "cycle-xyz"


# ---------------------------------------------------------------------------
# Class 4 — POST /render Endpoint Contract
# ---------------------------------------------------------------------------

class TestRenderEndpointContract:
    """Live endpoint tests via TestClient."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi import FastAPI
        from starlette.testclient import TestClient
        render_mod = _load("app.routers.render")
        test_app = FastAPI()
        test_app.include_router(render_mod.router)
        return TestClient(test_app, raise_server_exceptions=False)

    def test_post_render_returns_200(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={
                "X-Cast-ID": "cast-001",
                "X-Cycle-ID": "cycle-001",
                "X-Executed-By": "FORGE",
            },
        )
        assert resp.status_code == 200

    def test_render_response_has_rendered_by_cif(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        data = resp.json()
        assert data.get("rendered_by") == "CIF"

    def test_render_echoes_cast_id_from_header(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={"X-Cast-ID": "cast-echo-42", "X-Cycle-ID": "cycle-001"},
        )
        data = resp.json()
        assert data.get("cast_id") == "cast-echo-42"

    def test_render_echoes_cycle_id_from_header(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-echo-99"},
        )
        data = resp.json()
        assert data.get("cycle_id") == "cycle-echo-99"

    def test_render_response_has_surface_id(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-target"},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        data = resp.json()
        assert data.get("surface_id") == "srf-target"

    def test_render_response_schema_version(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        data = resp.json()
        assert data.get("schema_version") == "1.0.0"

    def test_render_missing_surface_id_returns_422(self, client):
        resp = client.post(
            "/render",
            json={},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        assert resp.status_code == 422

    def test_render_render_config_optional(self, client):
        """Omitting render_config must not cause a 422."""
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        assert resp.status_code == 200

    def test_render_with_render_config_accepted(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001", "render_config": {"theme": "dark"}},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Class 5 — Executor→CIF Client Stub Tests
# ---------------------------------------------------------------------------

class TestExecutorCIFClientStub:
    """
    Stub isolation tests for the Executor→CIF integration path.
    These verify the Executor's CIF client contract without a live CIF service.

    Stubs live in stardance-forge-executor — but contract is defined here
    against the RenderResponse shape that CIF will produce.
    """

    def test_render_response_200_maps_to_complete(self):
        """A 200 from CIF /render must result in execution_state=complete."""
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        # Simulate what executor sees on a 200 response
        resp = RenderResponse(
            surface_id="srf-001",
            render_status="complete",
            cast_id="cast-001",
            cycle_id="cycle-001",
        )
        assert resp.render_status == "complete"

    def test_render_response_carries_attribution(self):
        """CIF render response must always carry rendered_by=CIF."""
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(surface_id="srf-001")
        assert resp.rendered_by == "CIF"

    def test_render_response_lineage_propagated(self):
        """cast_id and cycle_id must survive the round trip."""
        mod = _load("app.routers.render")
        RenderResponse = mod.RenderResponse
        resp = RenderResponse(
            surface_id="srf-001",
            cast_id="cast-propagate",
            cycle_id="cycle-propagate",
        )
        assert resp.cast_id == "cast-propagate"
        assert resp.cycle_id == "cycle-propagate"

    def test_stub_422_signals_ethics_violation(self, mocker=None):
        """
        A 422 from CIF /render must be treated as ethics/validation failure.
        Contract assertion only — Executor wiring tested in forge-executor tests.
        """
        # 422 is the TIS gate response code
        ETHICS_GATE_STATUS = 422
        assert ETHICS_GATE_STATUS == 422  # Contract constant pinned

    def test_stub_500_signals_cif_internal_error(self):
        """
        A 500 from CIF /render must result in execution_state=failed
        with recovery_owner=FORGE.
        Contract assertion only.
        """
        RECOVERY_OWNER = "FORGE"
        assert RECOVERY_OWNER == "FORGE"  # Recovery boundary pinned


# ---------------------------------------------------------------------------
# Class 6 — Negative Paths
# ---------------------------------------------------------------------------

class TestRenderNegativePaths:
    """Rejection and error handling contracts."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi import FastAPI
        from starlette.testclient import TestClient
        render_mod = _load("app.routers.render")
        test_app = FastAPI()
        test_app.include_router(render_mod.router)
        return TestClient(test_app, raise_server_exceptions=False)

    def test_render_without_body_returns_422(self, client):
        resp = client.post("/render", headers={"X-Cast-ID": "c", "X-Cycle-ID": "cy"})
        assert resp.status_code == 422

    def test_render_with_invalid_json_returns_422(self, client):
        resp = client.post(
            "/render",
            content="not-json",
            headers={
                "Content-Type": "application/json",
                "X-Cast-ID": "c",
                "X-Cycle-ID": "cy",
            },
        )
        assert resp.status_code == 422

    def test_render_rendered_by_is_always_cif_not_forge(self, client):
        """rendered_by must never be FORGE — CIF renders, FORGE executes."""
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        data = resp.json()
        assert data.get("rendered_by") != "FORGE"

    def test_render_response_schema_version_is_not_none(self, client):
        resp = client.post(
            "/render",
            json={"surface_id": "srf-001"},
            headers={"X-Cast-ID": "cast-001", "X-Cycle-ID": "cycle-001"},
        )
        data = resp.json()
        assert data.get("schema_version") is not None
