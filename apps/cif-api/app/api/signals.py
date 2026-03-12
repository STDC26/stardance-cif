from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.signal import SignalEventIn, SignalEventOut
from app.services.signal_service import ingest_signal
from app.db.session import get_db

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("", response_model=SignalEventOut, status_code=201)
async def ingest_signal_endpoint(
    data: SignalEventIn,
    db: AsyncSession = Depends(get_db)
):
    event = await ingest_signal(db, data)
    return SignalEventOut(
        id=event.id,
        event_type=event.event_type,
        surface_id=event.surface_id,
        session_id=event.session_id,
        created_at=event.created_at.isoformat()
    )
