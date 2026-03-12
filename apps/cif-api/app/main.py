from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.surfaces import router as surfaces_router
from app.api.signals import router as signals_router

app = FastAPI(title="CIF API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(surfaces_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/health")
def health_v1():
    return {"status": "healthy", "version": "v1"}
