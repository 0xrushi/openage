#!/usr/bin/env python3

"""Integration test: query filtered entity state and print it.

Prerequisites:
- openage running (creates /tmp/openage_spawn.sock)

Invocation:

  cd /home/doraemon/Documents/openage/bin
  PYTHONPATH=. python3 /home/doraemon/Documents/openage/pythontests/integration/test_state_filtered_entities.py
"""

from __future__ import annotations

import json
import os
import sys

from openage.agent_control import OpenAgeAgent

def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def main() -> None:
    sock_path = "/tmp/openage_spawn.sock"
    if not os.path.exists(sock_path):
        die(f"IPC socket not found at {sock_path}. Start the game first.")

    agent = OpenAgeAgent(socket_path=sock_path, timeout_s=8.0)

    # Spawn a few movable entities under owner 0.
    for i in range(3):
        res = agent.act("spawn_character", entity_type="monk", position={"ne": 12 + i, "se": 12, "up": 0})
        if not res.ok:
            die(f"spawn_character failed: {res}")

    res_all = agent.act("get_state", query="entities")
    if not res_all.ok:
        die(f"get_state failed: {res_all}")

    res_filtered = agent.act("get_state", query="entities", owner=0, has="move", limit=50)
    if not res_filtered.ok:
        die(f"get_state (filtered) failed: {res_filtered}")

    print("# state|entities")
    print(json.dumps(res_all.data.get("state"), indent=2, sort_keys=True))
    print("\n# state|entities|owner=0|has=move|limit=50")
    print(json.dumps(res_filtered.data.get("state"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
