from __future__ import annotations

from enum import Enum


class ExecutionState(str, Enum):
    """
    FORGE execution lifecycle states.
    FORGE owns these. CIF does not.

    DRJ ruling P2-G2: FORGE owns execution-state authority.
    CIF owns render state only. Must not own execution transitions.
    """
    IDLE             = "idle"
    VALIDATING       = "validating"        # CastPayload + lineage + ethics check
    PROCESSING       = "processing"        # Active execution
    COMPLETE         = "complete"          # Execution finished, signal emitted
    PARTIAL_COMPLETE = "partial_complete"  # Some components completed
    FAILED           = "failed"            # Execution failed, recovery owner: FORGE


# Valid state transitions — enforced, not suggested
VALID_TRANSITIONS: dict[ExecutionState, list[ExecutionState]] = {
    ExecutionState.IDLE:             [ExecutionState.VALIDATING],
    ExecutionState.VALIDATING:       [ExecutionState.PROCESSING, ExecutionState.FAILED],
    ExecutionState.PROCESSING:       [ExecutionState.COMPLETE, ExecutionState.PARTIAL_COMPLETE, ExecutionState.FAILED],
    ExecutionState.COMPLETE:         [],           # Terminal
    ExecutionState.PARTIAL_COMPLETE: [],           # Terminal
    ExecutionState.FAILED:           [],           # Terminal — FORGE owns recovery
}


def transition(current: ExecutionState, next_state: ExecutionState) -> ExecutionState:
    """Enforce valid state transitions. Raises ValueError on invalid transition."""
    if next_state not in VALID_TRANSITIONS.get(current, []):
        raise ValueError(
            f"Invalid execution state transition: {current} → {next_state}. "
            f"Valid transitions from {current}: {VALID_TRANSITIONS[current]}"
        )
    return next_state
