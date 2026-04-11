"""
CIF AI Routing Policy — Phase-6 Track 1

Canonical task taxonomy and provider routing table.
Canonical task types are CIF workflow-aligned names.
Aliases are accepted internally but are not canonical taxonomy.
"""

import os
from enum import Enum


class AITaskType(str, Enum):
    # Local (Ollama) — CIF canonical
    SIGNAL_SUMMARY = "signal_summary"
    EXPERIMENT_SUMMARY = "experiment_summary"
    OPERATOR_ASSISTANT = "operator_assistant"
    ASSET_DRAFT = "asset_draft"

    # Remote (Anthropic) — CIF canonical
    ADVANCED_REASONING = "advanced_reasoning"

    # Aliases — internal use only
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    NARRATE = "narrate"
    INSIGHT = "insight"
    RECOMMEND = "recommend"
    EXPLAIN = "explain"


class AIProvider(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


LOCAL_TASKS: set[AITaskType] = {
    AITaskType.SIGNAL_SUMMARY,
    AITaskType.EXPERIMENT_SUMMARY,
    AITaskType.OPERATOR_ASSISTANT,
    AITaskType.ASSET_DRAFT,
    AITaskType.SUMMARIZE,
    AITaskType.CLASSIFY,
    AITaskType.EXTRACT,
}

REMOTE_TASKS: set[AITaskType] = {
    AITaskType.ADVANCED_REASONING,
    AITaskType.NARRATE,
    AITaskType.INSIGHT,
    AITaskType.RECOMMEND,
    AITaskType.EXPLAIN,
}


def resolve_provider(task_type: AITaskType) -> AIProvider:
    """Returns the canonical provider for a given task type."""
    if task_type in LOCAL_TASKS:
        return AIProvider.LOCAL
    return AIProvider.REMOTE


# ── Configuration ─────────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))
ANTHROPIC_TIMEOUT = float(os.getenv("ANTHROPIC_TIMEOUT", "30.0"))

# ── stardance-llm-service routing ──────────────────────────────────────────
STARDANCE_LLM_SERVICE_URL = os.getenv("STARDANCE_LLM_SERVICE_URL", "http://localhost:8003")

CIF_TO_LLM_TASK_MAP: dict[str, str] = {
    "advanced_reasoning": "specification_generation",
    "narrate": "specification_generation",
    "insight": "trait_mapping",
    "recommend": "structured_extraction",
    "explain": "specification_generation",
}
