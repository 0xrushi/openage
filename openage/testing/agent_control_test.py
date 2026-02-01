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
        srv.settimeout(2.0)
        ready.set()

        for i, (expected_prefix, response) in enumerate(expected):
            conn, _ = srv.accept()
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
        ]
        t = threading.Thread(target=_serve_many, args=(sock_path, expected, got, ready), daemon=True)
        t.start()

        ready.wait(timeout=2.0)

        agent = OpenAgeAgent(socket_path=sock_path, timeout_s=2.0)
        res = agent.act("spawn_character", entity_type="monk", position={"ne": pos.ne, "se": pos.se, "up": pos.up})

        t.join(timeout=2.0)
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
    finally:
        shutil.rmtree(tmpdir)
