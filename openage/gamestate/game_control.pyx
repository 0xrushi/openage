# Copyright 2024-2024 © openage authors. See copying.md for legal info.

"""
Python API for controlling a running openage game instance.

This module provides functions to spawn units in the actual running game.
"""

from libc.stdint cimport uint64_t


# Declare external C functions
cdef extern:
    uint64_t openage_python_spawn_unit(const char *, uint64_t, double, double, double)
    int openage_is_game_active()


def spawn_unit(
    str nyan_entity,
    int owner = 0,
    double ne = 5.0,
    double se = 5.0,
    double up = 0.0,
):
    """
    Spawn a unit in the running game at the specified position.

    This spawns a unit that will persist and be visible in the running game.
    The game must be running before calling this function.

    Args:
        nyan_entity: Fully qualified nyan object name (e.g., "hd_base.data.game_entity.generic.knight.knight.Knight")
        owner: Owner player ID (default: 0)
        ne: North-East coordinate (default: 5.0)
        se: South-East coordinate (default: 5.0)
        up: Up/height coordinate (default: 0.0)

    Returns:
        int: The entity ID of the spawned unit (or 0 on failure)

    Raises:
        RuntimeError: If no game is running

    Example:
        >>> from openage.gamestate import spawn_unit
        >>> # First start the game: ./run main --modpacks hd_base
        >>> entity_id = spawn_unit("hd_base.data.game_entity.generic.knight.knight.Knight", ne=10, se=10)
        >>> print(f"Spawned entity with ID: {entity_id}")
    """
    if not is_game_active():
        raise RuntimeError(
            "No game is currently running. "
            "Please start the game first using: ./run main --modpacks hd_base"
        )

    cdef bytes nyan_entity_bytes = nyan_entity.encode("utf-8")
    cdef char *nyan_entity_cpp = nyan_entity_bytes
    cdef uint64_t owner_id = <uint64_t> owner
    cdef uint64_t entity_id

    entity_id = openage_python_spawn_unit(
        nyan_entity_cpp,
        owner_id,
        ne,
        se,
        up
    )

    if entity_id == 0:
        raise RuntimeError(
            f"Failed to spawn unit '{nyan_entity}'. Check the game logs for details."
        )

    return int(entity_id)


def is_game_active():
    """
    Check if a game is currently running.

    Returns:
        bool: True if a game is running, False otherwise

    Example:
        >>> from openage.gamestate import is_game_active
        >>> if is_game_active():
        ...     print("Game is running!")
        ...     spawn_unit(...)
    """
    result = openage_is_game_active() != 0
    print(f"[DEBUG] Python is_game_active() returning: {result}")
    return result
