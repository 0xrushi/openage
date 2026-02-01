#!/usr/bin/env python3

"""Integration test: spawn -> patrol through waypoints.

Prerequisites:
- openage running (creates /tmp/openage_spawn.sock)

Invocation:

  cd /home/doraemon/Documents/openage/bin
  PYTHONPATH=. python3 /home/doraemon/Documents/openage/pythontests/integration/test_patrol.py
"""

from __future__ import annotations

import json
import os
import sys
import time

from openage.agent_control import OpenAgeAgent


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def main() -> None:
    sock_path = "/tmp/openage_spawn.sock"
    if not os.path.exists(sock_path):
        die(f"IPC socket not found at {sock_path}. Start the game first.")

    agent = OpenAgeAgent(socket_path=sock_path, timeout_s=8.0)

    # Spawn a monk at a known position.
    spawn = agent.act(
        "spawn_character",
        entity_type="monk",
        position={"ne": 10, "se": 10, "up": 0},
        tag="patrol_test",
    )
    if not spawn.ok:
        die(f"spawn failed: {spawn}")

    entity_id = spawn.data.get("entity_id")
    print(f"Spawned entity {entity_id}")

    # Define a patrol path with 3 waypoints.
    waypoints = [
        {"ne": 12, "se": 12, "up": 0},
        {"ne": 14, "se": 10, "up": 0},
        {"ne": 10, "se": 14, "up": 0},
    ]

    patrol = agent.act("patrol", tag="patrol_test", waypoints=waypoints)
    if not patrol.ok:
        die(f"patrol failed: {patrol}")

    print(f"Patrol result: {patrol}")
    assert patrol.data.get("waypoint_count") == 3, (
        f"Expected 3 waypoints, got {patrol.data.get('waypoint_count')}"
    )

    # Poll state to verify the unit starts moving away from spawn position.
    deadline = time.time() + 10.0
    moved = False

    while time.time() < deadline:
        state_res = agent.act("get_state", query="entities", id=entity_id)
        if not state_res.ok:
            die(f"get_state failed: {state_res}")

        state = state_res.data.get("state")
        entities = (state or {}).get("entities", []) if isinstance(state, dict) else []

        for ent in entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("id") != entity_id:
                continue
            pos = ent.get("pos")
            if isinstance(pos, dict):
                ne = float(pos.get("ne", 0.0))
                se = float(pos.get("se", 0.0))
                if abs(ne - 10.0) > 0.5 or abs(se - 10.0) > 0.5:
                    moved = True
            break

        if moved:
            break

        time.sleep(0.25)

    # Print final state.
    final = agent.act("get_state", query="entities", id=entity_id)
    if final.ok:
        print(json.dumps(final.data.get("state"), indent=2, sort_keys=True))
    else:
        print(final)

    if not moved:
        die(
            "Entity did not move away from spawn position within timeout. "
            "Patrol waypoints may not have been processed."
        )

    print("PASS: patrol integration test")


if __name__ == "__main__":
    main()
