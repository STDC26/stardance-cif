from typing import Any
from app.models.component import ComponentType

# TIS — Trait Integrity Standards (DRJ 2026-04-03)
# Aligned to CIDE ETHICS_MIN = 45. Previous value of 50 created a 45-49 gap band.
# FORGE logs TIS-F4 alert when ethics trait score < ETHICS_FLOOR_FORGE.
ETHICS_FLOOR_FORGE = 45

# Required fields per component type
COMPONENT_SCHEMAS: dict[ComponentType, dict[str, Any]] = {
    ComponentType.hero: {
        "required": ["headline"],
        "optional": ["subheadline", "primary_cta", "secondary_cta", "media_asset_id", "layout_variant"]
    },
    ComponentType.text_block: {
        "required": ["body"],
        "optional": ["title", "alignment", "max_width"]
    },
    ComponentType.image: {
        "required": ["asset_id", "alt_text"],
        "optional": ["caption", "aspect_ratio"]
    },
    ComponentType.video: {
        "required": ["asset_id"],
        "optional": ["poster_asset_id", "autoplay", "controls", "caption"]
    },
    ComponentType.cta: {
        "required": ["label", "action_type", "action_target"],
        "optional": ["style_variant", "tracking_label"]
    },
    ComponentType.form: {
        "required": ["form_type", "fields", "submit_label"],
        "optional": ["success_state", "destination"]
    },
    ComponentType.offer_stack: {
        "required": ["offer_title", "items", "price"],
        "optional": ["compare_at_price", "bonus_items", "urgency_text"]
    },
    ComponentType.social_proof: {
        "required": ["proof_type"],
        "optional": ["quotes", "rating", "review_count", "logo_asset_ids"]
    },
    ComponentType.testimonial: {
        "required": ["quote", "author_name"],
        "optional": ["author_title", "avatar_asset_id", "variant"]
    },
    ComponentType.faq: {
        "required": ["items"],
        "optional": ["default_open_index", "style_variant"]
    },
    ComponentType.diagnostic_entry: {
        "required": ["entry_label", "entry_mode", "diagnostic_id"],
        "optional": ["prefill_context", "tracking_label"]
    },
    ComponentType.trust_bar: {
        "required": ["items"],
        "optional": ["icon_asset_ids", "variant"]
    },
    ComponentType.content_grid: {
        "required": ["items"],
        "optional": ["columns", "gap", "style_variant"]
    },
}

def validate_component_config(
    component_type: ComponentType,
    config: dict[str, Any]
) -> list[str]:
    """
    Validate a component config against the registry schema.
    Returns a list of validation errors. Empty list = valid.
    """
    schema = COMPONENT_SCHEMAS.get(component_type)
    if not schema:
        return [f"Unknown component type: {component_type}"]

    errors = []
    for field in schema["required"]:
        if field not in config:
            errors.append(f"Missing required field '{field}' for component type '{component_type}'")
    return errors
