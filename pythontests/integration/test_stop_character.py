#!/usr/bin/env python3

"""Integration test: spawn -> move -> stop.

Prerequisites:
- openage running (creates /tmp/openage_spawn.sock)

Invocation:

  cd /home/doraemon/Documents/openage/bin
  PYTHONPATH=. python3 /home/doraemon/Documents/openage/pythontests/integration/test_stop_character.py
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

    spawn = agent.act("spawn_character", entity_type="monk", position={"ne": 14, "se": 14, "up": 0}, tag="stop_test")
    if not spawn.ok:
        die(f"spawn failed: {spawn}")

    mv = agent.act("move_character", tag="stop_test", destination={"ne": 18, "se": 18, "up": 0})
    if not mv.ok:
        die(f"move failed: {mv}")

    # Let the unit start moving.
    time.sleep(0.25)

    st = agent.act("stop_character", tag="stop_test")
    if not st.ok:
        die(f"stop failed: {st}")

    print(spawn)
    print(mv)
    print(st)


if __name__ == "__main__":
    main()
