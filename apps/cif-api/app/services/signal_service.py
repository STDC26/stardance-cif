from sqlalchemy.ext.asyncio import AsyncSession
from app.models.signal import SignalEvent
from app.schemas.signal import SignalEventIn


async def ingest_signal(db: AsyncSession, data: SignalEventIn) -> SignalEvent:
    event = SignalEvent(
        surface_id=data.surface_id,
        experiment_id=data.experiment_id,
        event_type=data.event_type,
        session_id=data.session_id,
        event_data={
            **data.event_data,
            **({"component_id": data.component_id} if data.component_id else {}),
            **({"component_type": data.component_type} if data.component_type else {}),
            **({"surface_version_id": str(data.surface_version_id)} if data.surface_version_id else {}),
        }
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
