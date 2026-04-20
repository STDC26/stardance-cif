"""Central config for service-to-service URLs and secrets.

Everything here is read at import time from environment variables. Prefer
this module over scattered ``os.getenv`` calls so operators can audit
every external dependency in one file.
"""

import os
from types import SimpleNamespace


# ── A2 Underwriting Service ──────────────────────────────────────────────────
# TEMP: using public Railway URL (Option B — public-route mode).
# Migrate to internal Railway hostname (Option A — private networking) once
# service-to-service networking is confirmed. See TCE-11 Option A follow-up.
A2_SERVICE_URL: str = os.environ.get(
    "A2_SERVICE_URL",
    "https://stardance-a2-underwriting-production.up.railway.app",
)
A2_API_KEY: str = os.environ.get("A2_API_KEY", "")
A2_TIMEOUT_SECONDS: float = float(os.environ.get("A2_TIMEOUT_SECONDS", "30.0"))


# ── Settings namespace (``settings.X`` access pattern) ──────────────────────
# Exposes each constant as an attribute on a single object for callers that
# prefer ``from app.core.config import settings`` over module-level imports.
settings = SimpleNamespace(
    A2_SERVICE_URL=A2_SERVICE_URL,
    A2_API_KEY=A2_API_KEY,
    A2_TIMEOUT_SECONDS=A2_TIMEOUT_SECONDS,
)
