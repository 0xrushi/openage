# Copyright 2024-2024 the openage authors. See copying.md for legal info.

"""
Python API for programmatic control of openage game units.

Provides functions to spawn entities, move units, and control gameplay
without requiring mouse input.
"""

from libcpp.string cimport string
from libcpp.vector cimport vector
from libc.stdint cimport uint64_t

from libopenage.util.path cimport Path as Path_cpp
from libopenage.pyinterface.pyobject cimport PyObj
from cpython.ref cimport PyObject
from libopenage.gamestate.demo.tests cimport spawn_nyan_entity as spawn_nyan_entity_c


def spawn_unit(
    str nyan_entity,
    list modpacks = None,
    int owner = 0,
    double ne = 5.0,
    double se = 5.0,
    double up = 0.0,
    str asset_dir = None,
    str cfg_dir = None,
):
    """
    Spawn a unit at the specified position.

    This creates a temporary simulation and spawns a unit, returning its entity ID.
    Note: This is intended for scripting/experiments, not for controlling the
    main game instance in real-time.

    Args:
        nyan_entity: Fully qualified nyan object name (e.g., "hd_base.data.game_entity.generic.knight.knight.Knight")
        modpacks: List of modpacks to load (e.g., ["hd_base"])
        owner: Owner player ID (default: 0)
        ne: North-East coordinate (default: 5.0)
        se: South-East coordinate (default: 5.0)
        up: Up/height coordinate (default: 0.0)
        asset_dir: Asset directory path
        cfg_dir: Config directory path

    Returns:
        int: The entity ID of the spawned unit

    Example:
        >>> from openage.gamestate.api import spawn_unit
        >>> entity_id = spawn_unit("hd_base.data.game_entity.generic.knight.knight.Knight",
        ...                        modpacks=["hd_base"],
        ...                        ne=10, se=10)
    """
    # Initialize C++<->Python interface if needed
    from argparse import Namespace
    from ..cppinterface.setup import setup as cpp_interface_setup
    cpp_interface_setup(Namespace(trap_exceptions=False))

    from ..cvar.location import get_config_path
    from ..assets import get_asset_path
    from ..util.fslike.union import Union

    root = Union().root
    root["assets"].mount(get_asset_path(asset_dir))
    root["cfg"].mount(get_config_path(cfg_dir))

    cdef Path_cpp root_cpp = Path_cpp(PyObj(<PyObject*>root.fsobj),
                                  root.parts)

    cdef vector[string] modpacks_vec
    if modpacks is not None:
        for modpack in modpacks:
            modpacks_vec.push_back(str(modpack).encode("utf-8"))

    cdef string nyan_entity_cpp = nyan_entity.encode("utf-8")
    cdef uint64_t owner_id = <uint64_t> owner
    cdef uint64_t entity_id

    with nogil:
        entity_id = spawn_nyan_entity_c(root_cpp,
                                        modpacks_vec,
                                        nyan_entity_cpp,
                                        owner_id,
                                        ne,
                                        se,
                                        up)

    return int(entity_id)


def move_unit(int entity_id, double ne, double se, double up=0.0):
    """
    Move a unit to the specified position.

    Note: This function requires access to the running game simulation,
    which is currently not directly exposed to Python. For now, this is
    a placeholder showing the intended API.

    Args:
        entity_id: The entity ID of the unit to move
        ne: North-East coordinate
        se: South-East coordinate
        up: Up/height coordinate (default: 0.0)

    Example:
        >>> from openage.gamestate.api import move_unit
        >>> move_unit(1234, ne=20, se=20)
    """
    # TODO: This requires access to the running GameSimulation
    # The implementation would call gamestate::event::SendCommandHandler
    # with a MOVE command type
    raise NotImplementedError(
        "move_unit requires access to the running game simulation. "
        "This feature is not yet implemented. Use the main game's "
        "right-click to move units for now."
    )


def select_unit(int entity_id):
    """
    Select a unit programmatically.

    Note: This function requires access to the running game controller,
    which is currently not directly exposed to Python.

    Args:
        entity_id: The entity ID of the unit to select

    Example:
        >>> from openage.gamestate.api import select_unit
        >>> select_unit(1234)
    """
    # TODO: This requires access to the running Controller
    raise NotImplementedError(
        "select_unit requires access to the running game controller. "
        "This feature is not yet implemented. Use left-click to select "
        "units for now."
    )


def cycle_spawn_type():
    """
    Cycle through available unit types for spawning.

    Note: This function requires access to the running game simulation,
    which is currently not directly exposed to Python.

    Example:
        >>> from openage.gamestate.api import cycle_spawn_type
        >>> cycle_spawn_type()
    """
    # TODO: This would send a cycle event to the SpawnEntityHandler
    raise NotImplementedError(
        "cycle_spawn_type requires access to the running game simulation. "
        "This feature is not yet implemented. Use Ctrl+Right-click in the "
        "main game to cycle spawn types."
    )


# Common unit type shortcuts for convenience
UNIT_TYPES = {
    "knight": "hd_base.data.game_entity.generic.knight.knight.Knight",
    "archer": "hd_base.data.game_entity.generic.archer.archer.Archer",
    "monk": "hd_base.data.game_entity.generic.monk.monk.Monk",
    "villager": "hd_base.data.game_entity.generic.villager.villager.Villager",
    "barracks": "hd_base.data.game_entity.generic.barracks.barracks.Barracks",
    "castle": "hd_base.data.game_entity.generic.castle.castle.Castle",
}


def spawn_unit_by_name(str unit_name, **kwargs):
    """
    Spawn a unit by common name using predefined shortcuts.

    Args:
        unit_name: Common unit name (e.g., "knight", "archer", "monk")
        **kwargs: Additional arguments passed to spawn_unit()

    Returns:
        int: The entity ID of the spawned unit

    Example:
        >>> from openage.gamestate.api import spawn_unit_by_name
        >>> entity_id = spawn_unit_by_name("knight", modpacks=["hd_base"], ne=10, se=10)
    """
    if unit_name not in UNIT_TYPES:
        raise ValueError(
            f"Unknown unit name '{unit_name}'. "
            f"Available units: {list(UNIT_TYPES.keys())}"
        )
    return spawn_unit(UNIT_TYPES[unit_name], **kwargs)
