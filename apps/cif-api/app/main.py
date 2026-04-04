import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.surfaces import router as surfaces_router
from app.api.signals import router as signals_router
from app.api.deployments import router as deployments_router
from app.api.public import router as public_router
from app.api.qds import router as qds_router
from app.api.internal import router as internal_router
from app.api.experiments import router as experiments_router
from app.api.analytics import router as analytics_router
from app.api.ai import router as ai_router
from app.api.retrieval import router as retrieval_router
from app.api.insights import router as insights_router
from app.api.copilot import router as copilot_router


from app.middleware.tis import TISMiddleware


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


app = FastAPI(title="CIF API", version="0.1.0")

app.add_middleware(TraceIDMiddleware)
app.add_middleware(TISMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://base-ui-seven.vercel.app", "https://base-ui.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes — no auth
app.include_router(public_router)

# Authenticated API routes
app.include_router(surfaces_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")
app.include_router(deployments_router, prefix="/api/v1")
app.include_router(qds_router, prefix="/api/v1")

# Experiments — has own /api/v1 prefix
app.include_router(experiments_router)

# Analytics — has own /api/v1 prefix
app.include_router(analytics_router)

# AI Provider — has own /api/v1 prefix
app.include_router(ai_router)

# Retrieval Layer — has own /api/v1 prefix
app.include_router(retrieval_router)

# Operator Intelligence — has own /api/v1 prefix
app.include_router(insights_router)

# Copilot — has own /api/v1 prefix
app.include_router(copilot_router)

# Internal routes — no auth, no /api/v1 prefix
app.include_router(internal_router)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/v1/health")
def health_v1():
    return {"status": "healthy", "version": "v1"}
