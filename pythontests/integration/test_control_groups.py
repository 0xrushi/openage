#!/usr/bin/env python3

"""Integration test: control groups (create, command, disband).

Prerequisites:
- openage running (creates /tmp/openage_spawn.sock)

Invocation:

  cd /home/doraemon/Documents/openage/bin
  PYTHONPATH=. python3 /home/doraemon/Documents/openage/pythontests/integration/test_control_groups.py
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

    # Spawn three monks at different positions and tag them.
    tags = ["grp_a", "grp_b", "grp_c"]
    entity_ids = []
    for i, tag in enumerate(tags):
        spawn = agent.act(
            "spawn_character",
            entity_type="monk",
            position={"ne": 10 + i * 2, "se": 10, "up": 0},
            tag=tag,
        )
        if not spawn.ok:
            die(f"spawn failed for tag {tag}: {spawn}")
        eid = spawn.data.get("entity_id")
        if not isinstance(eid, int):
            die(f"spawn returned no entity_id for tag {tag}: {spawn}")
        entity_ids.append(eid)
        print(f"Spawned {tag} -> entity {eid}")

    # Create a group from tags.
    cg = agent.act("create_group", group_id="squad", tags=tags)
    if not cg.ok:
        die(f"create_group failed: {cg}")
    print(f"Created group 'squad': {cg.data}")

    assert cg.data.get("member_count") == 3, (
        f"Expected 3 members, got {cg.data.get('member_count')}"
    )

    # Verify get_group.
    gg = agent.act("get_group", group_id="squad")
    if not gg.ok:
        die(f"get_group failed: {gg}")
    assert sorted(gg.data.get("members", [])) == sorted(entity_ids), (
        f"Group members mismatch: expected {sorted(entity_ids)}, got {sorted(gg.data.get('members', []))}"
    )

    # Command the group to move together.
    dest = {"ne": 20, "se": 20, "up": 0}
    cmd_move = agent.act("command_group", group_id="squad", action="move_character", destination=dest)
    if not cmd_move.ok:
        die(f"command_group move failed: {cmd_move}")
    print(f"Group move result: ok_count={cmd_move.data.get('ok_count')}, fail_count={cmd_move.data.get('fail_count')}")

    assert cmd_move.data.get("ok_count") == 3, (
        f"Expected 3 ok, got {cmd_move.data.get('ok_count')}"
    )

    # Let them move briefly, then stop the group.
    time.sleep(0.5)

    cmd_stop = agent.act("command_group", group_id="squad", action="stop_character")
    if not cmd_stop.ok:
        die(f"command_group stop failed: {cmd_stop}")
    print(f"Group stop result: ok_count={cmd_stop.data.get('ok_count')}")

    # Query state to confirm entities exist.
    state_res = agent.act("get_state", query="entities", owner=0, has="move", limit=50)
    if state_res.ok:
        state = state_res.data.get("state")
        entities = (state or {}).get("entities", []) if isinstance(state, dict) else []
        found_ids = {ent.get("id") for ent in entities if isinstance(ent, dict)}
        for eid in entity_ids:
            if eid not in found_ids:
                die(f"Entity {eid} not found in state after group commands")
        print(f"All {len(entity_ids)} group members found in state")

    # Disband.
    dg = agent.act("disband_group", group_id="squad")
    if not dg.ok:
        die(f"disband_group failed: {dg}")
    print(f"Disbanded group 'squad': disbanded_count={dg.data.get('disbanded_count')}")

    # Verify group no longer exists.
    gg2 = agent.act("get_group", group_id="squad")
    assert not gg2.ok, "get_group should fail after disband"

    print("PASS: control groups integration test")


if __name__ == "__main__":
    main()
