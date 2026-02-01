#!/usr/bin/env python3

"""Unit tests for the repo-level spawn.py wrapper."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from unittest.mock import patch

from openage.testing.testing import assert_raises, assert_value, result


def _load_spawn_module():
    """Load spawn.py from repo root as a module."""

    def find_repo_root() -> str:
        """Find the source tree root that contains spawn.py."""

        # 1) Prefer CMakeCache.txt from the build dir.
        # When running from `bin/`, this file is available and contains
        # the source directory as CMAKE_HOME_DIRECTORY.
        build_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cache_path = os.path.join(build_root, "CMakeCache.txt")
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf8") as f:
                for line in f:
                    if line.startswith("CMAKE_HOME_DIRECTORY") and "=" in line:
                        _, value = line.split("=", 1)
                        value = value.strip()
                        if value:
                            return value

        # 2) Optional env override.
        env_root = os.environ.get("OPENAGE_SOURCE_DIR")
        if env_root:
            return os.path.abspath(env_root)

        # 3) Fallback: walk upwards and look for spawn.py.
        cur = os.path.abspath(os.path.dirname(__file__))
        for _ in range(10):
            candidate = os.path.join(cur, "spawn.py")
            if os.path.exists(candidate):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

        raise RuntimeError("failed to locate repo root containing spawn.py")

    repo_root = find_repo_root()
    spawn_path = os.path.join(repo_root, "spawn.py")

    spec = importlib.util.spec_from_file_location("openage_spawn_wrapper_under_test", spawn_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to create import spec for spawn.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test():
    spawn = _load_spawn_module()

    # find_spawn_tool: prefers bin/libopenage/gamestate/spawn_tool when present.
    with patch.object(spawn.os.path, "exists") as mock_exists, \
         patch.object(spawn.os, "access") as mock_access:

        def exists_side_effect(path):
            return path.endswith(os.path.join("bin", "libopenage", "gamestate", "spawn_tool"))

        mock_exists.side_effect = exists_side_effect
        mock_access.return_value = True
        tool = spawn.find_spawn_tool()
        assert_value(tool.endswith(os.path.join("bin", "libopenage", "gamestate", "spawn_tool")), True)

    # find_spawn_tool: glob fallback in .bin/**/libopenage/gamestate/spawn_tool
    with patch.object(spawn.os.path, "exists") as mock_exists, \
         patch.object(spawn.os, "access", return_value=True), \
         patch.object(spawn.glob, "glob", return_value=["/tmp/build/libopenage/gamestate/spawn_tool"]):

        def exists_side_effect_glob(path):
            # Force candidate paths to look missing so we actually hit the glob fallback.
            if path.endswith(os.path.join("bin", "spawn_tool")):
                return False
            if path.endswith(os.path.join("bin", "libopenage", "gamestate", "spawn_tool")):
                return False
            return True

        mock_exists.side_effect = exists_side_effect_glob
        tool = spawn.find_spawn_tool()
        assert_value(tool, "/tmp/build/libopenage/gamestate/spawn_tool")

    # spawn_unit: parses "Entity ID: <n>" output and uses subprocess correctly.
    with patch.object(spawn, "find_spawn_tool", return_value="/tmp/spawn_tool"), \
         patch.object(spawn.subprocess, "run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/tmp/spawn_tool"],
            returncode=0,
            stdout="Entity ID: 42\nMessage: ok\n",
            stderr="",
        )
        with patch("builtins.print"):
            entity_id = spawn.spawn_unit(
                "hd_base.data.game_entity.generic.monk.monk.Monk",
                owner=0,
                ne=14.0,
                se=14.0,
                up=0.0,
            )
        assert_value(entity_id, 42)
        assert_value(mock_run.call_count, 1)
        called_cmd = mock_run.call_args[0][0]
        assert_value(called_cmd[:2], ["/tmp/spawn_tool", "hd_base.data.game_entity.generic.monk.monk.Monk"])

    # spawn_unit: accepts bare integer output.
    with patch.object(spawn, "find_spawn_tool", return_value="/tmp/spawn_tool"), \
         patch.object(spawn.subprocess, "run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/tmp/spawn_tool"],
            returncode=0,
            stdout="123\n",
            stderr="",
        )
        with patch("builtins.print"):
            assert_value(spawn.spawn_unit("x"), 123)

    # spawn_unit: non-zero return code raises.
    with patch.object(spawn, "find_spawn_tool", return_value="/tmp/spawn_tool"), \
         patch.object(spawn.subprocess, "run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/tmp/spawn_tool"],
            returncode=1,
            stdout="",
            stderr="boom",
        )
        with assert_raises(RuntimeError):
            result(spawn.spawn_unit("x"))

    # spawn_unit: empty output raises.
    with patch.object(spawn, "find_spawn_tool", return_value="/tmp/spawn_tool"), \
         patch.object(spawn.subprocess, "run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["/tmp/spawn_tool"],
            returncode=0,
            stdout="\n",
            stderr="",
        )
        with assert_raises(RuntimeError):
            result(spawn.spawn_unit("x"))
