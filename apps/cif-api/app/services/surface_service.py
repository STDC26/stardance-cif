from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.surface import Surface, SurfaceVersion
from app.models.component import Component, SurfaceComponent, ComponentType
from app.schemas.surface import SurfaceCreateIn, ResolvedSurface, ResolvedComponent
from app.registry.component_registry import validate_component_config
import uuid


async def create_surface(db: AsyncSession, data: SurfaceCreateIn) -> tuple[Surface, list[str]]:
    """Create a surface with versioned components. Returns (surface, validation_errors)."""
    errors = []

    # Validate all component configs upfront
    for section in data.sections:
        for comp in section.components:
            errs = validate_component_config(comp.component_type, comp.config)
            errors.extend(errs)

    if errors:
        return None, errors

    # Create surface
    surface = Surface(
        name=data.name,
        description=data.description,
        type=data.type,
        status="draft",
        config={}
    )
    db.add(surface)
    await db.flush()

    # Create initial version
    version = SurfaceVersion(
        surface_id=surface.id,
        version_number=1,
        status="draft",
        config={"sections": [s.model_dump() for s in data.sections]}
    )
    db.add(version)
    await db.flush()

    # Create and link components
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


async def resolve_surface(db: AsyncSession, surface_id: uuid.UUID) -> ResolvedSurface | None:
    """Resolve a surface into its full component tree."""
    result = await db.execute(
        select(Surface).where(Surface.id == surface_id)
    )
    surface = result.scalar_one_or_none()
    if not surface:
        return None

    # Get latest version
    version_result = await db.execute(
        select(SurfaceVersion)
        .where(SurfaceVersion.surface_id == surface_id)
        .order_by(SurfaceVersion.version_number.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    if not version:
        return None

    # Get all surface components with their component data
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

    sections = [
        {"section_id": k, "components": v}
        for k, v in sections_map.items()
    ]

    return ResolvedSurface(
        surface_id=str(surface.id),
        surface_version_id=str(version.id),
        name=surface.name,
        status=surface.status,
        sections=sections,
        components=resolved_components
    )
