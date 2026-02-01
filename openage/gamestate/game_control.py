# Copyright 2026-2026 the openage authors. See copying.md for legal info.

"""Python API for controlling a running openage game instance.

This is a pure-Python fallback implementation that talks to the engine IPC
socket ("/tmp/openage_spawn.sock").

If a Cython-based implementation exists (game_control.pyx), it will take
precedence at import time.
"""

from __future__ import annotations

import os
import socket

from openage.agent_control.ipc import IpcClient
from openage.agent_control.schema import Position


def is_game_active(socket_path: str = "/tmp/openage_spawn.sock") -> bool:
    """Return True if a running game IPC server is reachable."""

    if not os.path.exists(socket_path):
        return False

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            sock.connect(socket_path)
            return True
    except OSError:
        return False


def spawn_unit(
    nyan_entity: str,
    owner: int = 0,
    ne: float = 5.0,
    se: float = 5.0,
    up: float = 0.0,
    socket_path: str = "/tmp/openage_spawn.sock",
):
    """Spawn a unit in the running game via engine IPC.

    Returns:
        int: entity id (can be 0 depending on game state)
    """

    if not is_game_active(socket_path=socket_path):
        raise RuntimeError(
            "No game IPC server reachable. Start the game first using: ./run main --modpacks hd_base"
        )

    client = IpcClient(socket_path=socket_path, timeout_s=8.0)
    res = client.spawn(nyan_entity=str(nyan_entity), owner=int(owner), pos=Position(ne=float(ne), se=float(se), up=float(up)))
    if not res.ok:
        raise RuntimeError(res.error or "spawn failed")

    return int(res.data.get("entity_id", 0))
