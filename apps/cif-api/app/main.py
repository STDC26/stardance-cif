from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.surfaces import router as surfaces_router
from app.api.signals import router as signals_router
from app.api.deployments import router as deployments_router
from app.api.public import router as public_router
from app.api.qds import router as qds_router
from app.api.internal import router as internal_router
from app.api.experiments import router as experiments_router
from app.api.analytics import router as analytics_router

app = FastAPI(title="CIF API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

# Internal routes — no auth, no /api/v1 prefix
app.include_router(internal_router)

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/health")
def health_v1():
    return {"status": "healthy", "version": "v1"}
