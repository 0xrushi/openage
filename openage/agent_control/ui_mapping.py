# Copyright 2026-2026 the openage authors. See copying.md for legal info.

"""UI gesture -> intent mapping.

This module is intentionally data-only: it does not generate input events.
It exists to document how human UI interactions correspond to agent actions.
"""

from __future__ import annotations


GESTURE_TO_ACTION = {
    "Ctrl+RightClick": {"name": "switch_active_character", "kwargs": {}},
    "Ctrl+LeftClick": {"name": "spawn_character", "kwargs": {"position": "cursor"}},
    "RightClick": {"name": "move_character", "kwargs": {"destination": "cursor"}},
}
