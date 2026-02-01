#!/usr/bin/env python3

"""Integration test: select_by_query + move.

Prerequisites:
- openage running (creates /tmp/openage_spawn.sock)

Invocation:

  cd /home/doraemon/Documents/openage/bin
  PYTHONPATH=. python3 /home/doraemon/Documents/openage/pythontests/integration/test_select_by_query.py
"""

from __future__ import annotations

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

    # Spawn two monks far apart but safely within common map bounds.
    a = agent.act("spawn_character", entity_type="monk", position={"ne": 12, "se": 12, "up": 0}, tag="m_a")
    b = agent.act("spawn_character", entity_type="monk", position={"ne": 18, "se": 18, "up": 0}, tag="m_b")
    if not a.ok or not b.ok:
        die(f"spawn failed: a={a} b={b}")

    # Select the monk nearest to (0,0) among owner=0 move-capable entities.
    sel = agent.act("select_by_query", owner=0, has="move", strategy="nearest", near={"ne": 10, "se": 10, "up": 0})
    if not sel.ok:
        die(f"select_by_query failed: {sel}")

    # Move the selected entity.
    mv = agent.act("move_character", destination={"ne": 16, "se": 16, "up": 0})
    if not mv.ok:
        die(f"move_character failed: {mv}")

    # Print a state snapshot.
    time.sleep(0.25)
    state = agent.act("get_state", query="entities", owner=0, has="move", limit=50)
    print(sel)
    print(mv)
    print(state)


if __name__ == "__main__":
    main()
