# Copyright 2024-2024 the openage authors. See copying.md for legal info.

"""
Python API for controlling a running openage game instance.

This module provides functions to spawn, move, and select units
in the actual running game (not temporary simulations).
"""

from libcpp.string cimport string
from libcpp.vector cimport vector
from libc.stdint cimport uint64_t
from libc.stddef cimport size_t

from libopenage.gamestate.global_simulation cimport global_simulation
from libopenage.gamestate.simulation cimport GameSimulation
from libopenage.util.path cimport Path as Path_cpp
from libopenage.pyinterface.pyobject cimport PyObj
from cpython.ref cimport PyObject


cdef class LiveGame:
    """
    Wrapper for accessing the running game simulation.

    This class provides methods to control units in the live game.
    """
    cdef GameSimulation* simulation

    def __cinit__(self):
        """
        Initialize the live game controller.

        Raises an exception if no game is currently running.
        """
        cdef auto sim_ptr = global_simulation().get()
        if not sim_ptr:
            raise RuntimeError(
                "No running game found. "
                "Please start the game first using: ./run main --modpacks hd_base"
            )
        self.simulation = sim_ptr.get()

    def spawn_unit(
        self,
        str nyan_entity,
        int owner = 0,
        double ne = 5.0,
        double se = 5.0,
        double up = 0.0,
    ):
        """
        Spawn a unit in the running game at the specified position.

        This spawns a unit that will persist and be visible in the running game.

        Args:
            nyan_entity: Fully qualified nyan object name (e.g., "hd_base.data.game_entity.generic.knight.knight.Knight")
            owner: Owner player ID (default: 0)
            ne: North-East coordinate (default: 5.0)
            se: South-East coordinate (default: 5.0)
            up: Up/height coordinate (default: 0.0)

        Returns:
            int: The entity ID of the spawned unit

        Raises:
            RuntimeError: If no game is running

        Example:
            >>> game = LiveGame()
            >>> entity_id = game.spawn_unit("hd_base.data.game_entity.generic.knight.knight.Knight", ne=10, se=10)
        """
        # This is a placeholder - actual implementation requires:
        # 1. Access to GameSimulation's get_spawner()
        # 2. Create spawn event via EventLoop
        # 3. Handle threading between Python and game loop
        raise NotImplementedError(
            "spawn_unit in live game requires additional C++ bindings. "
            "Currently, use Ctrl+Left Click in the game interface."
        )

    def move_unit(self, size_t entity_id, double ne, double se, double up=0.0):
        """
        Move a unit to a new position in the running game.

        Args:
            entity_id: The entity ID of the unit to move
            ne: North-East coordinate
            se: South-East coordinate
            up: Up/height coordinate (default: 0.0)

        Raises:
            RuntimeError: If no game is running
            ValueError: If entity_id doesn't exist

        Example:
            >>> game = LiveGame()
            >>> game.move_unit(1234, ne=20, se=20)
        """
        # This is a placeholder - actual implementation requires:
        # 1. Access to GameSimulation's get_commander()
        # 2. Create MOVE command via EventLoop
        # 3. Handle threading between Python and game loop
        raise NotImplementedError(
            "move_unit in live game requires additional C++ bindings. "
            "Currently, select the unit with Left Click, then Right Click to move."
        )

    def select_unit(self, size_t entity_id):
        """
        Select a unit programmatically in the running game.

        Args:
            entity_id: The entity ID of the unit to select

        Raises:
            RuntimeError: If no game is running
            ValueError: If entity_id doesn't exist

        Example:
            >>> game = LiveGame()
            >>> game.select_unit(1234)
        """
        # This is a placeholder - actual implementation requires:
        # 1. Access to Controller's set_selected() method
        # 2. Expose Controller to Python
        # 3. Handle threading between Python and game loop
        raise NotImplementedError(
            "select_unit in live game requires additional C++ bindings. "
            "Currently, use Left Click to select units."
        )

    def get_spawner(self):
        """
        Get the spawner for creating entities.

        This is a low-level method for advanced use.

        Returns:
            The spawner object

        Raises:
            RuntimeError: If no game is running
        """
        # This would expose the Spawner object to Python
        # Requires additional Cython bindings
        raise NotImplementedError(
            "get_spawner requires additional C++ bindings"
        )

    def get_commander(self):
        """
        Get the commander for sending commands.

        This is a low-level method for advanced use.

        Returns:
            The commander object

        Raises:
            RuntimeError: If no game is running
        """
        # This would expose the Commander object to Python
        # Requires additional Cython bindings
        raise NotImplementedError(
            "get_commander requires additional C++ bindings"
        )


def get_live_game():
    """
    Get the live game controller.

    Returns:
        LiveGame: An instance of the live game controller

    Raises:
        RuntimeError: If no game is currently running

    Example:
        >>> from openage.gamestate import get_live_game
        >>> game = get_live_game()
        >>> game.spawn_unit(...)
    """
    return LiveGame()


def is_game_running():
    """
    Check if a game is currently running.

    Returns:
        bool: True if a game is running, False otherwise

    Example:
        >>> from openage.gamestate import is_game_running
        >>> if is_game_running():
        ...     print("Game is running!")
        ...     game = get_live_game()
    """
    cdef auto sim_ptr = global_simulation().get()
    return sim_ptr != nullptr
