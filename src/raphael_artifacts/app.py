"""Raphael service: raphael-artifacts."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from raphael_contracts.errors import ErrorResponse
from raphael_artifacts.routes import router

app = FastAPI(
    title="raphael-artifacts",
    description="Artifact CRUD, metadata, lifecycle, snapshots",
    version="0.1.0",
    openapi_url="/v1/artifacts/openapi.json" if "/v1/artifacts" else "/openapi.json",
)

app.include_router(router, prefix="/v1/artifacts" if "/v1/artifacts" else "")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "raphael-artifacts"}


@app.exception_handler(Exception)
async def unhandled(_request, exc: Exception) -> JSONResponse:
    err = ErrorResponse(code="internal_error", message=str(exc))
    return JSONResponse(status_code=500, content=err.model_dump())
