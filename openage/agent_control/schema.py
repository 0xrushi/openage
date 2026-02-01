# Copyright 2026-2026 the openage authors. See copying.md for legal info.

"""Action schema for agent-style control.

This module defines a small, composable set of intent-level actions that are
UI-agnostic. Results are always structured so callers (humans, scripts, LLMs)
can reason about success/failure deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True, slots=True)
class Position:
    ne: float
    se: float
    up: float = 0.0

    @classmethod
    def from_obj(cls, obj: Any) -> "Position":
        if isinstance(obj, Position):
            return obj
        if not isinstance(obj, dict):
            raise TypeError("position must be a Position or dict")
        try:
            ne = float(obj["ne"])
            se = float(obj["se"])
            up = float(obj.get("up", 0.0))
        except (KeyError, ValueError, TypeError) as exc:
            raise TypeError("position must have numeric keys ne,se[,up]") from exc
        return cls(ne=ne, se=se, up=up)


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Structured result for an agent action."""

    ok: bool
    supported: bool
    action: str
    data: Dict[str, Any]
    error: Optional[str] = None

    @classmethod
    def ok_result(cls, action: str, **data: Any) -> "ActionResult":
        return cls(ok=True, supported=True, action=action, data=dict(data), error=None)

    @classmethod
    def not_supported(cls, action: str, message: str, **data: Any) -> "ActionResult":
        return cls(ok=False, supported=False, action=action, data=dict(data), error=message)

    @classmethod
    def error_result(cls, action: str, message: str, **data: Any) -> "ActionResult":
        return cls(ok=False, supported=True, action=action, data=dict(data), error=message)


# Declarative action definitions.
ACTIONS: List[Dict[str, Any]] = [
    {
        "name": "get_state",
        "description": "Query game state snapshot from the running game (IPC)",
        "inputs": {
            "query": "string (currently: 'entities')",
        },
    },
    {
        "name": "switch_active_character",
        "description": "Switch control/spawn type to the next available character",
        "inputs": {},
    },
    {
        "name": "spawn_character",
        "description": "Spawn a character/entity at a given position",
        "inputs": {
            "entity_type": "string (alias like 'monk' or full nyan id)",
            "position": "object {ne,se,up?}",
            "owner": "int (default: 0)",
            "tag": "string (optional, local name for later selection)",
        },
    },
    {
        "name": "select_character",
        "description": "Select a character by entity id",
        "inputs": {
            "character_id": "int (optional)",
            "tag": "string (optional)",
            "spawn_index": "int (optional; 0-based, negatives allowed)",
        },
    },
    {
        "name": "move_character",
        "description": "Move a character to a destination position",
        "inputs": {
            "character_id": "int (optional; defaults to current selection)",
            "tag": "string (optional)",
            "spawn_index": "int (optional)",
            "destination": "object {ne,se,up?}",
        },
    },
]
