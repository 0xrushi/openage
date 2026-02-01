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
            "owner": "int (optional; filter entities by owner)",
            "id": "int (optional; filter to a single entity id)",
            "has": "string (optional; e.g. 'move' or 'selectable')",
            "limit": "int (optional; max number of results)",
        },
    },
    {
        "name": "select_by_query",
        "description": "Select a character using a query over state (agent-side)",
        "inputs": {
            "owner": "int (optional; passed to get_state)",
            "has": "string (optional; passed to get_state)",
            "limit": "int (optional; passed to get_state)",
            "strategy": "string (optional; 'nearest' or 'first'; default: 'nearest')",
            "near": "object {ne,se,up?} (required for strategy='nearest')",
        },
    },
    {
        "name": "stop_character",
        "description": "Stop a character (clear its command queue and idle)",
        "inputs": {
            "character_id": "int (optional; defaults to current selection)",
            "tag": "string (optional)",
            "spawn_index": "int (optional)",
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
    {
        "name": "patrol",
        "description": "Clear command queue and walk through a sequence of waypoints",
        "inputs": {
            "character_id": "int (optional; defaults to current selection)",
            "tag": "string (optional)",
            "spawn_index": "int (optional)",
            "waypoints": "list of objects {ne,se,up?} (at least one required)",
        },
    },
    {
        "name": "attack_target",
        "description": "Attack-move toward a target entity (moves attacker to target's current position)",
        "inputs": {
            "target": "int (required; target entity id)",
            "character_id": "int (optional; defaults to current selection)",
            "tag": "string (optional)",
            "spawn_index": "int (optional)",
        },
    },
    {
        "name": "create_group",
        "description": "Create a named control group from unit ids, tags, or spawn indices",
        "inputs": {
            "group_id": "string (required; name or number for the group)",
            "character_ids": "list[int] (optional)",
            "tags": "list[string] (optional)",
            "spawn_indices": "list[int] (optional)",
        },
    },
    {
        "name": "get_group",
        "description": "Return the character ids in a control group",
        "inputs": {
            "group_id": "string (required)",
        },
    },
    {
        "name": "disband_group",
        "description": "Remove a control group (does not affect the units themselves)",
        "inputs": {
            "group_id": "string (required)",
        },
    },
    {
        "name": "command_group",
        "description": "Issue a command (move_character, stop_character, patrol, attack_target) to every unit in a group",
        "inputs": {
            "group_id": "string (required)",
            "action": "string (move_character | stop_character | patrol | attack_target)",
            "destination": "object {ne,se,up?} (required for move_character)",
            "waypoints": "list of objects {ne,se,up?} (required for patrol)",
            "target": "int (required for attack_target; target entity id)",
        },
    },
]
