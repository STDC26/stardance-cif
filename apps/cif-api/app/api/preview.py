"""Preview + Review API (TCE-10).

Asset-agnostic preview tokens with an independent review lifecycle. Any
CIF asset (conversion_surface, qds) can be wrapped in a token and shared
for approval before deployment. The token itself is the bearer credential
for public read + review endpoints.

Endpoints:
  POST /api/v1/preview                   → create token (requires API key)
  GET  /api/v1/preview/{preview_id}      → fetch token (token is auth)
  POST /api/v1/preview/{preview_id}/review → approve | reject (token is auth)
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.db.session import get_db
from app.models.preview import PreviewToken
from app.models.signal import EventType, SignalEvent


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/preview", tags=["preview"])


_RENDERER_BASE = "https://sd-chubs-renderer.vercel.app"


class PreviewCreateBody(BaseModel):
    asset_id: UUID
    asset_type: str
    asset_slug: str
    version_id: Optional[UUID] = None
    expires_in_hours: int = Field(default=48, ge=1, le=720)


class PreviewReviewBody(BaseModel):
    decision: str
    notes: Optional[str] = None


def _build_url(slug: str, preview_id: str) -> str:
    return f"{_RENDERER_BASE}/?slug={slug}&preview={preview_id}"


def _ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _serialize(token: PreviewToken) -> dict:
    return {
        "preview_id": token.preview_id,
        "asset_id": str(token.asset_id),
        "asset_type": token.asset_type,
        "asset_slug": token.asset_slug,
        "version_id": str(token.version_id) if token.version_id else None,
        "preview_url": _build_url(token.asset_slug, token.preview_id),
        "review_state": token.review_state,
        "expires_at": _ensure_aware(token.expires_at).isoformat(),
        "reviewer_notes": token.reviewer_notes,
        "reviewed_at": (
            _ensure_aware(token.reviewed_at).isoformat()
            if token.reviewed_at else None
        ),
        "created_at": (
            _ensure_aware(token.created_at).isoformat()
            if token.created_at else None
        ),
    }


async def _fetch_active_token(db: AsyncSession, preview_id: str) -> PreviewToken:
    """Return the token or raise 404 if missing / expired."""
    row = await db.execute(
        select(PreviewToken).where(PreviewToken.preview_id == preview_id)
    )
    token = row.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    if _ensure_aware(token.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Preview expired")
    return token


@router.post("")
async def create_preview(
    body: PreviewCreateBody,
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Create a preview token. API key required."""
    secret = secrets.token_urlsafe(16)
    preview_id = f"prev-{secret[:8]}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours)

    token = PreviewToken(
        preview_id=preview_id,
        asset_id=body.asset_id,
        asset_type=body.asset_type,
        asset_slug=body.asset_slug,
        version_id=body.version_id,
        expires_at=expires_at,
        created_by=api_key,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return _serialize(token)


@router.get("/{preview_id}")
async def get_preview(preview_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch a preview token. The token itself is the authorization."""
    token = await _fetch_active_token(db, preview_id)
    return _serialize(token)


@router.post("/{preview_id}/review")
async def review_preview(
    preview_id: str,
    body: PreviewReviewBody,
    db: AsyncSession = Depends(get_db),
):
    """Submit a review decision. 409 if already approved/rejected."""
    token = await _fetch_active_token(db, preview_id)
    if token.review_state != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Preview already {token.review_state}",
        )
    if body.decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=422,
            detail="decision must be 'approve' or 'reject'",
        )

    new_state = "approved" if body.decision == "approve" else "rejected"
    token.review_state = new_state
    token.reviewer_notes = body.notes
    token.reviewed_at = datetime.now(timezone.utc)

    # Emit asset_reviewed signal — best-effort; never fail the review on a
    # signal-emission error.
    try:
        db.add(SignalEvent(
            surface_id=token.asset_id,
            event_type=EventType.asset_reviewed,
            event_data={
                "preview_id": token.preview_id,
                "decision": body.decision,
                "asset_type": token.asset_type,
                "asset_slug": token.asset_slug,
                "reviewer_notes": body.notes,
                "surface_version_id": (
                    str(token.version_id) if token.version_id else None
                ),
            },
        ))
    except Exception as e:
        logger.warning("asset_reviewed signal emission failed: %s", e)

    await db.commit()
    await db.refresh(token)

    return {
        "preview_id": token.preview_id,
        "review_state": token.review_state,
        "reviewed_at": _ensure_aware(token.reviewed_at).isoformat(),
        "notes": token.reviewer_notes,
    }
