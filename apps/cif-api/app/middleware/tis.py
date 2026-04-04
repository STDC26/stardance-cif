from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.registry.component_registry import ETHICS_FLOOR_FORGE


class TISMiddleware(BaseHTTPMiddleware):
    """
    Trust & Insight Surface enforcement middleware.
    Intercepts execution requests. Validates ethics floor.
    Cannot be bypassed. Stateless.

    DRJ ruling UQ-3 + P2-G3: ETHICS_FLOOR_FORGE = 45
    All execution flows must pass through TIS.
    """

    async def dispatch(self, request: Request, call_next):
        if self._is_execution_route(request):
            ethics_score = self._extract_ethics_score(request)
            if ethics_score is not None and self._is_below_ethics_floor(ethics_score):
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": "Ethics floor violation",
                        "ethics_score": ethics_score,
                        "ethics_floor": ETHICS_FLOOR_FORGE,
                        "tis_gate": "TIS-F4",
                        "ruling": "UQ-3",
                    },
                )
        return await call_next(request)

    def _is_execution_route(self, request: Request) -> bool:
        execution_paths = ["/resolve", "/surfaces", "/deploy"]
        return any(request.url.path.startswith(p) for p in execution_paths)

    def _extract_ethics_score(self, request: Request) -> int | None:
        score = request.headers.get("X-Ethics-Score")
        if score is not None:
            try:
                return int(score)
            except ValueError:
                return None
        return None

    def _is_below_ethics_floor(self, score: int) -> bool:
        """Return True if score is below ETHICS_FLOOR_FORGE (i.e. must be rejected)."""
        return score < ETHICS_FLOOR_FORGE
