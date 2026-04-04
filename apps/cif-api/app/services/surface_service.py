from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.surface import Surface, SurfaceVersion, ReviewState
from app.models.component import Component, SurfaceComponent
from app.schemas.surface import SurfaceCreateIn, ResolvedSurface, ResolvedComponent
from app.schemas.cast_payload import CastPayload, DecisionExplanationSummary
from app.registry.component_registry import validate_component_config
from app.core.slugify import slugify, unique_suffix
import uuid


async def generate_unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while True:
        result = await db.execute(select(Surface).where(Surface.slug == slug))
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base}-{unique_suffix()}"


async def create_surface(db: AsyncSession, data: SurfaceCreateIn) -> tuple[Surface | None, list[str]]:
    errors = []
    for section in data.sections:
        for comp in section.components:
            errs = validate_component_config(comp.component_type, comp.config)
            errors.extend(errs)
    if errors:
        return None, errors

    slug = await generate_unique_slug(db, data.name)

    surface = Surface(
        name=data.name,
        slug=slug,
        description=data.description,
        type=data.type,
        status="draft",
        config={}
    )
    db.add(surface)
    await db.flush()

    version = SurfaceVersion(
        surface_id=surface.id,
        version_number=1,
        status="draft",
        review_state=ReviewState.draft,
        config={"sections": [s.model_dump() for s in data.sections]}
    )
    db.add(version)
    await db.flush()

    for section in data.sections:
        for idx, comp_data in enumerate(section.components):
            component = Component(
                name=comp_data.name,
                component_type=comp_data.component_type,
                config=comp_data.config
            )
            db.add(component)
            await db.flush()

            surface_component = SurfaceComponent(
                surface_version_id=version.id,
                component_id=component.id,
                section_id=section.section_id,
                position=idx,
                config=comp_data.config
            )
            db.add(surface_component)

    await db.commit()
    await db.refresh(surface)
    return surface, []


async def resolve_surface(
    db: AsyncSession,
    surface_id: uuid.UUID,
    cycle_id: str,
    trace_id: str,
    cast_id: str,
    cast_payload: CastPayload,
) -> ResolvedSurface | None:
    result = await db.execute(select(Surface).where(Surface.id == surface_id))
    surface = result.scalar_one_or_none()
    if not surface:
        return None

    version_result = await db.execute(
        select(SurfaceVersion)
        .where(SurfaceVersion.surface_id == surface_id)
        .order_by(SurfaceVersion.version_number.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    if not version:
        return None

    sc_result = await db.execute(
        select(SurfaceComponent, Component)
        .join(Component, SurfaceComponent.component_id == Component.id)
        .where(SurfaceComponent.surface_version_id == version.id)
        .order_by(SurfaceComponent.section_id, SurfaceComponent.position)
    )
    rows = sc_result.all()

    resolved_components = []
    sections_map: dict[str, list] = {}

    for sc, comp in rows:
        rc = ResolvedComponent(
            component_id=str(comp.id),
            component_type=comp.component_type,
            name=comp.name,
            section_id=sc.section_id,
            position=sc.position,
            config=comp.config
        )
        resolved_components.append(rc)
        if sc.section_id not in sections_map:
            sections_map[sc.section_id] = []
        sections_map[sc.section_id].append(rc.model_dump())

    sections = [{"section_id": k, "components": v} for k, v in sections_map.items()]

    return ResolvedSurface(
        surface_id=str(surface.id),
        surface_version_id=str(version.id),
        name=surface.name,
        status=surface.status,
        sections=sections,
        components=resolved_components,
        cast_payload=cast_payload,
        cycle_id=cycle_id,
        trace_id=trace_id,
        cast_id=cast_id,
    )
