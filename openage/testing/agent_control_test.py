#!/usr/bin/env python3

"""Unit tests for openage.agent_control (pure python agent surface)."""

from __future__ import annotations

import os
import shutil
import socket
import tempfile
import threading

from openage.agent_control.agent import OpenAgeAgent
from openage.agent_control.catalog import resolve_entity_type
from openage.agent_control.schema import Position
from openage.testing.testing import assert_value, result


def _serve_many(socket_path: str, expected: list[tuple[str, str]], out_requests: list[dict], ready: threading.Event):
    # Ensure the directory exists and no stale socket is present.
    try:
        os.unlink(socket_path)
    except FileNotFoundError:
        pass

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        srv.bind(socket_path)
        srv.listen(1)
        srv.settimeout(10.0)
        ready.set()

        for i, (expected_prefix, response) in enumerate(expected):
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                out_requests.append({"raw": "", "ok_prefix": False})
                break
            try:
                data = conn.recv(4096)
                req: dict[str, object] = {
                    "raw": data.decode("utf-8", errors="replace"),
                    "ok_prefix": False,
                }
                req["ok_prefix"] = str(req["raw"]).startswith(expected_prefix)
                out_requests.append(req)
                conn.sendall(response.encode("utf-8"))
            finally:
                conn.close()
    finally:
        srv.close()


def test():
    # Catalog: aliases resolve.
    assert_value(resolve_entity_type("monk"), "hd_base.data.game_entity.generic.monk.monk.Monk")

    # Spawn: agent formats request and parses response.
    tmpdir = tempfile.mkdtemp(prefix="openage_agent_control_test_")
    try:
        sock_path = os.path.join(tmpdir, "spawn.sock")
        got = []
        pos = Position(ne=14.0, se=14.0, up=0.0)
        ready = threading.Event()

        expected = [
            (
                "spawn|hd_base.data.game_entity.generic.monk.monk.Monk|0|14.000000|14.000000|0.000000",
                "123|SUCCESS: Spawned monk",
            ),
            (
                "move|123|20.000000|20.000000|0.000000",
                "1|SUCCESS: Move queued",
            ),
            (
                "state|entities",
                '1|{"entities":[{"id":123,"owner":0,"pos":{"ne":14.0,"se":14.0,"up":0.0}}]}',
            ),
            (
                "state|entities|owner=0|has=move|limit=10",
                '1|{"entities":[{"id":123,"owner":0,"can_move":true,"selectable":false,"pos":{"ne":14.0,"se":14.0,"up":0.0}}]}',
            ),
            (
                "state|entities|owner=0|has=move|limit=50",
                '1|{"entities":['
                '{"id":1,"owner":0,"can_move":true,"selectable":false,"pos":{"ne":1.0,"se":1.0,"up":0.0}},'
                '{"id":2,"owner":0,"can_move":true,"selectable":false,"pos":{"ne":9.0,"se":9.0,"up":0.0}}'
                ']}',
            ),
            (
                "stop|1",
                "1|SUCCESS: Stop queued",
            ),
            (
                "patrol|1|5.000000|5.000000|0.000000|10.000000|10.000000|0.000000|15.000000|15.000000|0.000000",
                "1|SUCCESS: Patrol queued with 3 waypoint(s)",
            ),
            # attack_target: entity 1 attacks entity 123.
            (
                "attack|1|123",
                "1|SUCCESS: Attack-move queued toward entity 123",
            ),
            # attack_target with bad target (entity does not exist).
            (
                "attack|1|999",
                "0|ERROR: Target entity does not exist",
            ),
            # command_group: stop two members (entity 123 and entity 1).
            (
                "stop|123",
                "1|SUCCESS: Stop queued",
            ),
            (
                "stop|1",
                "1|SUCCESS: Stop queued",
            ),
            # command_group: move two members.
            (
                "move|123|30.000000|30.000000|0.000000",
                "1|SUCCESS: Move queued",
            ),
            (
                "move|1|30.000000|30.000000|0.000000",
                "1|SUCCESS: Move queued",
            ),
            # command_group: attack_target two members.
            (
                "attack|123|42",
                "1|SUCCESS: Attack-move queued toward entity 42",
            ),
            (
                "attack|1|42",
                "1|SUCCESS: Attack-move queued toward entity 42",
            ),
        ]
        t = threading.Thread(target=_serve_many, args=(sock_path, expected, got, ready), daemon=True)
        t.start()

        ready.wait(timeout=2.0)

        agent = OpenAgeAgent(socket_path=sock_path, timeout_s=2.0)
        res = agent.act("spawn_character", entity_type="monk", position={"ne": pos.ne, "se": pos.se, "up": pos.up})

        assert_value(got[0].get("ok_prefix"), True)
        assert_value(res.ok, True)
        assert_value(res.supported, True)
        assert_value(res.action, "spawn_character")
        assert_value(res.data.get("entity_id"), 123)

        # Move sends a move command (now supported at IPC level).
        res2 = agent.act("move_character", character_id=123, destination={"ne": 20, "se": 20, "up": 0})
        assert_value(got[1].get("ok_prefix"), True)
        assert_value(res2.ok, True)
        assert_value(res2.supported, True)
        assert_value(res2.data.get("character_id"), 123)

        res3 = agent.act("get_state", query="entities")
        assert_value(got[2].get("ok_prefix"), True)
        assert_value(res3.ok, True)
        assert_value(res3.supported, True)
        state = res3.data.get("state")
        assert_value(isinstance(state, dict), True)

        res4 = agent.act("get_state", query="entities", owner=0, has="move", limit=10)
        assert_value(got[3].get("ok_prefix"), True)
        assert_value(res4.ok, True)

        res5 = agent.act("select_by_query", owner=0, has="move", strategy="nearest", near={"ne": 0, "se": 0, "up": 0})
        assert_value(got[4].get("ok_prefix"), True)
        assert_value(res5.ok, True)
        assert_value(res5.data.get("character_id"), 1)

        res6 = agent.act("stop_character", character_id=1)
        assert_value(got[5].get("ok_prefix"), True)
        assert_value(res6.ok, True)
        assert_value(res6.data.get("character_id"), 1)

        # Patrol queues multiple waypoints in a single IPC command.
        res7 = agent.act(
            "patrol",
            character_id=1,
            waypoints=[
                {"ne": 5, "se": 5, "up": 0},
                {"ne": 10, "se": 10, "up": 0},
                {"ne": 15, "se": 15, "up": 0},
            ],
        )
        assert_value(got[6].get("ok_prefix"), True)
        assert_value(res7.ok, True)
        assert_value(res7.data.get("character_id"), 1)
        assert_value(res7.data.get("waypoint_count"), 3)

        # --- attack_target tests ---

        # attack_target: entity 1 attacks entity 123 (IPC resolves target position).
        res_atk = agent.act("attack_target", character_id=1, target=123)
        assert_value(got[7].get("ok_prefix"), True)
        assert_value(res_atk.ok, True)
        assert_value(res_atk.data.get("character_id"), 1)
        assert_value(res_atk.data.get("target_id"), 123)

        # attack_target with bad target (server returns error).
        res_atk_bad = agent.act("attack_target", character_id=1, target=999)
        assert_value(got[8].get("ok_prefix"), True)
        assert_value(res_atk_bad.ok, False)

        # attack_target with no character selected and no selector fails.
        agent2 = OpenAgeAgent(socket_path=sock_path, timeout_s=2.0)
        res_atk_nosel = agent2.act("attack_target", target=123)
        assert_value(res_atk_nosel.ok, False)

        # attack_target with bad target type fails.
        res_atk_badtype = agent.act("attack_target", target="not_an_int")
        assert_value(res_atk_badtype.ok, False)

        # --- Control group tests (agent-local + IPC for command_group) ---

        # create_group: requires at least one member source.
        bad_group = agent.act("create_group", group_id="empty")
        assert_value(bad_group.ok, False)

        # create_group using character_ids directly (no IPC needed).
        cg1 = agent.act("create_group", group_id="alpha", character_ids=[123, 1])
        assert_value(cg1.ok, True)
        assert_value(cg1.data.get("member_count"), 2)
        assert_value(cg1.data.get("members"), [123, 1])

        # get_group returns the members.
        gg1 = agent.act("get_group", group_id="alpha")
        assert_value(gg1.ok, True)
        assert_value(gg1.data.get("members"), [123, 1])

        # get_group on unknown group fails.
        gg_bad = agent.act("get_group", group_id="nope")
        assert_value(gg_bad.ok, False)

        # create_group from tags: agent._entities_by_tag was populated by the spawn with tag.
        # The spawn above used no tag, but the first spawn returned entity 123.
        # Let's use spawn_indices to test that path.
        cg2 = agent.act("create_group", group_id="beta", spawn_indices=[0])
        assert_value(cg2.ok, True)
        assert_value(cg2.data.get("members"), [123])

        # Duplicate ids are deduplicated.
        cg3 = agent.act("create_group", group_id="dupes", character_ids=[123, 123, 1])
        assert_value(cg3.ok, True)
        assert_value(cg3.data.get("member_count"), 2)

        # command_group: stop all members in "alpha" (2 IPC calls).
        cg_stop = agent.act("command_group", group_id="alpha", action="stop_character")
        assert_value(got[9].get("ok_prefix"), True)
        assert_value(got[10].get("ok_prefix"), True)
        assert_value(cg_stop.ok, True)
        assert_value(cg_stop.data.get("ok_count"), 2)
        assert_value(cg_stop.data.get("fail_count"), 0)

        # command_group: move all members in "alpha" (2 IPC calls).
        cg_move = agent.act(
            "command_group",
            group_id="alpha",
            action="move_character",
            destination={"ne": 30, "se": 30, "up": 0},
        )
        assert_value(got[11].get("ok_prefix"), True)
        assert_value(got[12].get("ok_prefix"), True)
        assert_value(cg_move.ok, True)
        assert_value(cg_move.data.get("ok_count"), 2)

        # command_group: attack_target all members in "alpha" (2 IPC calls).
        cg_atk = agent.act(
            "command_group",
            group_id="alpha",
            action="attack_target",
            target=42,
        )
        assert_value(got[13].get("ok_prefix"), True)
        assert_value(got[14].get("ok_prefix"), True)
        assert_value(cg_atk.ok, True)
        assert_value(cg_atk.data.get("ok_count"), 2)

        # command_group: unsupported action fails.
        cg_bad_action = agent.act("command_group", group_id="alpha", action="dance")
        assert_value(cg_bad_action.ok, False)

        # command_group: unknown group fails.
        cg_bad_group = agent.act("command_group", group_id="nope", action="stop_character")
        assert_value(cg_bad_group.ok, False)

        # disband_group removes the group.
        dg1 = agent.act("disband_group", group_id="alpha")
        assert_value(dg1.ok, True)
        assert_value(dg1.data.get("disbanded_count"), 2)

        # disband_group on unknown group fails.
        dg_bad = agent.act("disband_group", group_id="alpha")
        assert_value(dg_bad.ok, False)

        t.join(timeout=2.0)
    finally:
        shutil.rmtree(tmpdir)
