#!/usr/bin/env python3
"""
Simple Python wrapper for C++ spawn_tool.

Usage: ./spawn.py <entity_type> [owner] [ne] [se] [up]

Examples:
    ./spawn.py hd_base.data.game_entity.generic.knight.knight.Knight 0 10 10
    ./spawn.py hd_base.data.game_entity.generic.archer.archer.Archer
"""

import glob
import os
import re
import subprocess
import sys


def find_spawn_tool():
    """Find the spawn_tool executable."""
    repo_root = os.path.abspath(os.path.dirname(__file__))

    # Common locations in this repo.
    candidates = [
        os.path.join(repo_root, "bin", "spawn_tool"),
        os.path.join(repo_root, "bin", "libopenage", "gamestate", "spawn_tool"),
    ]
    for tool_path in candidates:
        if os.path.exists(tool_path) and os.access(tool_path, os.X_OK):
            return tool_path

    # Fallback: search CMake build dirs.
    for tool_path in sorted(glob.glob(os.path.join(repo_root, ".bin", "**", "libopenage", "gamestate", "spawn_tool"), recursive=True)):
        if os.path.exists(tool_path) and os.access(tool_path, os.X_OK):
            return tool_path

    return None


def spawn_unit(nyan_entity, owner=0, ne=5.0, se=5.0, up=0.0):
    """
    Spawn a unit using C++ spawn_tool.

    Args:
        nyan_entity: Fully qualified nyan object name
        owner: Owner player ID (default: 0)
        ne: North-East coordinate (default: 5.0)
        se: South-East coordinate (default: 5.0)
        up: Up/height coordinate (default: 0.0)

    Returns:
        int: Entity ID on success

    Raises:
        RuntimeError: If spawn_tool not found or spawn fails
    """
    spawn_tool = find_spawn_tool()
    if not spawn_tool:
        raise RuntimeError(
            "spawn_tool not found! "
            "It may still be building. Run 'make' to complete build."
        )

    # Build command
    cmd = [
        spawn_tool,
        nyan_entity,
        str(owner),
        str(ne),
        str(se),
        str(up)
    ]

    # Execute
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to spawn unit!\n"
            f"Error: {result.stderr}"
        )

    # Parse entity ID from stdout.
    stdout = (result.stdout or "").strip()
    if not stdout:
        raise RuntimeError("spawn_tool returned empty output")

    # Accept either a bare integer or lines like: "Entity ID: <id>".
    m = re.search(r"\bEntity ID:\s*(\d+)\b", stdout)
    if m:
        entity_id = int(m.group(1))
        print(f"Spawned unit with ID: {entity_id}")
        return entity_id

    try:
        entity_id = int(stdout)
        print(f"Spawned unit with ID: {entity_id}")
        return entity_id
    except ValueError:
        raise RuntimeError(f"Unexpected output: {stdout}")


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    nyan_entity = sys.argv[1]
    owner = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    ne = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
    se = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
    up = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0

    try:
        entity_id = spawn_unit(nyan_entity, owner, ne, se, up)
        print(f"Success: Entity ID = {entity_id}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
