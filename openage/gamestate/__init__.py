# Copyright 2023-2023 © openage authors. See copying.md for legal info.

"""
openage game simulation
"""

# Import test API (temporary simulations)
try:
    from .api import (
        spawn_unit as test_spawn_unit,
        spawn_unit_by_name,
        move_unit,
        select_unit,
        cycle_spawn_type,
        UNIT_TYPES,
    )
except (ImportError, ModuleNotFoundError):
    test_spawn_unit = None
    spawn_unit_by_name = None
    move_unit = None
    select_unit = None
    cycle_spawn_type = None
    UNIT_TYPES = None

# Import live game control API (actual running game)
has_live_game_control = False
live_spawn_unit = None
is_game_active = None

try:
    from .game_control import (
        spawn_unit as live_spawn_unit,
        is_game_active,
    )
    has_live_game_control = True
except (ImportError, ModuleNotFoundError) as e:
    print(f"[DEBUG] Failed to import game_control: {e}")
    pass

# Export available functions
# spawn_unit refers to LIVE game spawn if available
if has_live_game_control:
    spawn_unit = live_spawn_unit
    __all__ = [
        "spawn_unit",
        "is_game_active",
    ]
else:
    spawn_unit = None
    __all__ = []

# Also export test functions
if spawn_unit_by_name is not None:
    __all__.extend([
        "spawn_unit_by_name",
        "UNIT_TYPES",
    ])

# Export move_unit and select_unit from test API (they don't do anything currently)
if move_unit is not None:
    __all__.append("move_unit")
if select_unit is not None:
    __all__.append("select_unit")
