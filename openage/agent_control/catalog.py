# Copyright 2026-2026 the openage authors. See copying.md for legal info.

"""Friendly entity catalog for agent calls."""

from __future__ import annotations

from typing import Dict, List


# Keep this list intentionally small and stable.
# Users can always pass a fully-qualified nyan id instead.
UNIT_TYPES: Dict[str, str] = {
    "knight": "hd_base.data.game_entity.generic.knight.knight.Knight",
    "archer": "hd_base.data.game_entity.generic.archer.archer.Archer",
    "monk": "hd_base.data.game_entity.generic.monk.monk.Monk",
    "villager": "hd_base.data.game_entity.generic.villager.villager.Villager",
    "barracks": "hd_base.data.game_entity.generic.barracks.barracks.Barracks",
    "castle": "hd_base.data.game_entity.generic.castle.castle.Castle",
}


def list_unit_types() -> List[str]:
    return sorted(UNIT_TYPES.keys())


def resolve_entity_type(entity_type: str) -> str:
    """Resolve an alias or pass through full nyan ids."""

    if not isinstance(entity_type, str) or not entity_type:
        raise TypeError("entity_type must be a non-empty string")

    # Heuristic: fully-qualified nyan ids contain dots.
    if "." in entity_type:
        return entity_type

    key = entity_type.strip().lower()
    if key in UNIT_TYPES:
        return UNIT_TYPES[key]

    raise ValueError(
        f"Unknown entity_type '{entity_type}'. "
        f"Known aliases: {list_unit_types()}"
    )
