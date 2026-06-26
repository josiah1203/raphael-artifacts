"""API routes for raphael-artifacts."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["raphael-artifacts"])


@router.get("")
def list_root() -> dict[str, str]:
  return {"service": "raphael-artifacts", "status": "stub"}
