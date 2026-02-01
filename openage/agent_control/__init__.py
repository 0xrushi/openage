# Copyright 2026-2026 the openage authors. See copying.md for legal info.

"""Intent-first (agent-friendly) control surface for openage."""

from .agent import OpenAgeAgent
from .schema import ACTIONS, ActionResult, Position

__all__ = [
    "ACTIONS",
    "ActionResult",
    "OpenAgeAgent",
    "Position",
]
