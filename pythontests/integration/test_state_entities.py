#!/usr/bin/env python3

"""Integration test: spawn, move, query state.

Prerequisites:
- openage running (creates /tmp/openage_spawn.sock)

Recommended invocation (from build dir):

  # Note: /home/doraemon/Documents/openage/bin is a symlink into .bin/<build>/
  cd /home/doraemon/Documents/openage/bin
  PYTHONPATH=. python3 ../../pythontests/integration/test_state_entities.py

Alternative (absolute path):

  cd /home/doraemon/Documents/openage/bin
  PYTHONPATH=. python3 /home/doraemon/Documents/openage/pythontests/integration/test_state_entities.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from openage.agent_control import OpenAgeAgent as _OpenAgeAgent


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def main() -> None:
    # Ensure the IPC socket exists (game running).
    sock_path = "/tmp/openage_spawn.sock"
    if not os.path.exists(sock_path):
        die(f"IPC socket not found at {sock_path}. Start the game first.")

    OpenAgeAgent = None  # type: ignore[assignment]
    try:
        from openage.agent_control import OpenAgeAgent as _OpenAgeAgent
        OpenAgeAgent = _OpenAgeAgent  # type: ignore[assignment]
    except ModuleNotFoundError as exc:
        die(
            "Failed to import openage. Run from the build dir with PYTHONPATH set, e.g.\n"
            "  cd /home/doraemon/Documents/openage/bin\n"
            "  PYTHONPATH=. python3 ../pythontests/integration/test_state_entities.py\n"
            f"\nOriginal error: {exc}"
        )

    if OpenAgeAgent is None:
        die("OpenAgeAgent import failed")

    agent = OpenAgeAgent(socket_path=sock_path)  # type: ignore[misc]

    spawn = agent.act(
        "spawn_character",
        entity_type="monk",
        position={"ne": 14, "se": 14, "up": 0},
        tag="monk_test",
    )
    if not spawn.ok:
        die(f"spawn_character failed: {spawn}")

    entity_id = spawn.data.get("entity_id")
    if not isinstance(entity_id, int):
        die(f"spawn_character returned no entity_id: {spawn}")

    move = agent.act(
        "move_character",
        tag="monk_test",
        destination={"ne": 20, "se": 20, "up": 0},
    )
    if not move.ok:
        die(f"move_character failed: {move}")

    # Poll state until we can see the entity and (ideally) observe movement.
    deadline = time.time() + 10.0
    seen = False
    moved = False

    while time.time() < deadline:
        state_res = agent.act("get_state", query="entities")
        if not state_res.ok:
            die(f"get_state failed: {state_res}")

        state = state_res.data.get("state")
        entities = (state or {}).get("entities", []) if isinstance(state, dict) else []

        for ent in entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("id") != entity_id:
                continue
            seen = True
            pos = ent.get("pos")
            if isinstance(pos, dict):
                ne = float(pos.get("ne", 0.0))
                se = float(pos.get("se", 0.0))
                # if we are no longer exactly at spawn position, movement is happening.
                if abs(ne - 14.0) > 1e-6 or abs(se - 14.0) > 1e-6:
                    moved = True
            break

        if seen and moved:
            break

        time.sleep(0.25)

    # Print final state snapshot (human-visible).
    final_state_res = agent.act("get_state", query="entities")
    if final_state_res.ok:
        print(json.dumps(final_state_res.data.get("state"), indent=2, sort_keys=True))
    else:
        print(final_state_res)

    if not seen:
        die(f"Entity id {entity_id} not found in state within timeout")
    if not moved:
        die(
            "Entity was found in state but movement was not observed within timeout. "
            "This can happen if the simulation is paused or movement speed is zero."
        )


if __name__ == "__main__":
    main()
