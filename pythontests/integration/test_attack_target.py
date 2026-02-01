#!/usr/bin/env python3

"""Integration test: spawn an enemy unit, spawn an attacker, move attacker toward enemy.

Prerequisites:
- openage running (creates /tmp/openage_spawn.sock)

Invocation:

  make pytest FILE=pythontests/integration/test_attack_target.py
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

    agent = OpenAgeAgent(socket_path=sock_path, timeout_s=12.0)

    # Spawn enemy unit (owner=1) at a known position.
    target_spawn = agent.act(
        "spawn_character",
        entity_type="archer",
        position={"ne": 16, "se": 16, "up": 0},
        owner=1,
        tag="enemy",
    )
    if not target_spawn.ok:
        die(f"spawn target failed: {target_spawn}")

    enemy_id = target_spawn.data.get("entity_id")
    if not isinstance(enemy_id, int):
        die(f"spawn target returned no entity_id: {target_spawn}")

    print(f"enemy    (id={enemy_id}, owner=1): spawned at (16, 16)")

    # Small delay so the engine finishes processing the first spawn.
    time.sleep(0.5)

    # Spawn attacker away from the target (owner=0) so team colors differ.
    attacker_spawn = agent.act(
        "spawn_character",
        entity_type="archer",
        position={"ne": 12, "se": 12, "up": 0},
        owner=0,
        tag="attacker",
    )
    if not attacker_spawn.ok:
        die(f"spawn attacker failed: {attacker_spawn}")

    attacker_id = attacker_spawn.data.get("entity_id")
    if not isinstance(attacker_id, int):
        die(f"spawn attacker returned no entity_id: {attacker_spawn}")

    print(f"attacker (id={attacker_id}, owner=0): spawned at (12, 12)")

    # Attack-move the attacker toward the enemy entity.
    atk = agent.act("attack_target", tag="attacker", target=enemy_id)
    if not atk.ok:
        die(f"attack_target failed: {atk}")

    print(f"attack_target result: {atk}")

    # Poll state to verify attacker is moving toward the enemy.
    deadline = time.time() + 10.0
    moved = False
    while time.time() < deadline:
        poll_res = agent.act("get_state", query="entities", id=attacker_id)
        if not poll_res.ok:
            die(f"get_state failed: {poll_res}")

        poll_state = poll_res.data.get("state")
        poll_entities = (poll_state or {}).get("entities", []) if isinstance(poll_state, dict) else []
        for ent in poll_entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("id") != attacker_id:
                continue
            pos = ent.get("pos")
            if isinstance(pos, dict):
                ne = float(pos.get("ne", 0.0))
                se = float(pos.get("se", 0.0))
                # If moved away from spawn position (12, 12), movement is happening.
                if abs(ne - 12.0) > 1e-6 or abs(se - 12.0) > 1e-6:
                    moved = True
            break

        if moved:
            break
        time.sleep(0.25)

    if not moved:
        die(
            "Attacker was found in state but movement toward enemy was not observed "
            "within timeout. This can happen if the simulation is paused."
        )

    print("OK: attacker moved toward enemy")


if __name__ == "__main__":
    main()
