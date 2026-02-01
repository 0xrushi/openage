# Copyright 2026-2026 the openage authors. See copying.md for legal info.

"""IPC transport for the engine spawn socket."""

from __future__ import annotations

import socket
import json
from typing import Tuple

from .schema import ActionResult, Position


class IpcClient:
    def __init__(self, socket_path: str = "/tmp/openage_spawn.sock", timeout_s: float = 2.0):
        self.socket_path = socket_path
        self.timeout_s = timeout_s

    def request(self, command: str) -> Tuple[bool, str]:
        """Send a raw command and return (ok, response_text)."""

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout_s)
                sock.connect(self.socket_path)
                sock.sendall(command.encode("utf-8"))

                chunks = []
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
                    chunks.append(data)

                return True, b"".join(chunks).decode("utf-8", errors="replace").strip()
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def _format_spawn_command(nyan_entity: str, owner: int, pos: Position) -> str:
        # Match spawn_tool style: 6 decimal places.
        return (
            "spawn|"
            + nyan_entity
            + "|"
            + str(int(owner))
            + "|"
            + f"{pos.ne:.6f}"
            + "|"
            + f"{pos.se:.6f}"
            + "|"
            + f"{pos.up:.6f}"
        )

    @staticmethod
    def _parse_response(response: str) -> Tuple[int, str]:
        # Response format: <entity_id>|<message>
        if "|" not in response:
            return 0, response

        left, right = response.split("|", 1)
        try:
            entity_id = int(left.strip())
        except ValueError:
            entity_id = 0

        return entity_id, right.strip()

    def spawn(self, nyan_entity: str, owner: int, pos: Position) -> ActionResult:
        action = "spawn_character"
        cmd = self._format_spawn_command(nyan_entity, owner, pos)

        ok, response = self.request(cmd)
        if not ok:
            return ActionResult.error_result(
                action,
                f"IPC request failed: {response}",
                socket_path=self.socket_path,
                command=cmd,
            )

        entity_id, server_message = self._parse_response(response)

        # Protocol note: entity ids can be 0 in some game states.
        # Prefer the message prefix to determine success/failure.
        msg = (server_message or "").strip()
        if msg.startswith("ERROR:"):
            return ActionResult.error_result(
                action,
                msg,
                entity_id=entity_id,
                server_message=server_message,
                command=cmd,
            )

        if msg.startswith("SUCCESS:"):
            return ActionResult.ok_result(action, entity_id=entity_id, message=server_message)

        # Fallback for unexpected servers: treat non-positive ids as failure.
        if entity_id < 0:
            return ActionResult.error_result(
                action,
                msg or "spawn failed",
                entity_id=entity_id,
                server_message=server_message,
                command=cmd,
            )

        return ActionResult.ok_result(action, entity_id=entity_id, message=server_message)

    def move(self, entity_id: int, destination: Position) -> ActionResult:
        action = "move_character"
        cmd = (
            "move|"
            + str(int(entity_id))
            + "|"
            + f"{destination.ne:.6f}"
            + "|"
            + f"{destination.se:.6f}"
            + "|"
            + f"{destination.up:.6f}"
        )

        ok, response = self.request(cmd)
        if not ok:
            return ActionResult.error_result(
                action,
                f"IPC request failed: {response}",
                socket_path=self.socket_path,
                command=cmd,
            )

        # Backwards compatibility: older engine builds only replied to spawn.
        if not response:
            return ActionResult.not_supported(
                action,
                "IPC server returned empty response (likely running an older game build without move support). Restart the game.",
                character_id=int(entity_id),
                command=cmd,
            )

        status_code, server_message = self._parse_response(response)
        if status_code == 0:

            if not server_message or server_message.startswith("ERROR: Invalid command"):
                return ActionResult.not_supported(
                    action,
                    "move not supported by the running IPC server (restart the game with the rebuilt binary).",
                    character_id=int(entity_id),
                    server_message=server_message,
                    command=cmd,
                )

            return ActionResult.error_result(
                action,
                server_message,
                character_id=int(entity_id),
                server_message=server_message,
                command=cmd,
            )

        return ActionResult.ok_result(
            action,
            character_id=int(entity_id),
            message=server_message,
        )

    def stop(self, entity_id: int) -> ActionResult:
        action = "stop_character"
        cmd = "stop|" + str(int(entity_id))

        ok, response = self.request(cmd)
        if not ok:
            return ActionResult.error_result(
                action,
                f"IPC request failed: {response}",
                socket_path=self.socket_path,
                command=cmd,
            )

        if not response:
            return ActionResult.error_result(action, "IPC server returned empty response", command=cmd)

        status_code, server_message = self._parse_response(response)
        if status_code == 0:
            return ActionResult.error_result(
                action,
                server_message or "stop failed",
                character_id=int(entity_id),
                server_message=server_message,
                command=cmd,
            )

        return ActionResult.ok_result(action, character_id=int(entity_id), message=server_message)

    def patrol(self, entity_id: int, waypoints: list) -> ActionResult:
        action = "patrol"
        # Format: patrol|<entity_id>|<ne1>|<se1>|<up1>[|<ne2>|<se2>|<up2>...]
        cmd_parts = ["patrol", str(int(entity_id))]
        for wp in waypoints:
            cmd_parts.append(f"{wp.ne:.6f}")
            cmd_parts.append(f"{wp.se:.6f}")
            cmd_parts.append(f"{wp.up:.6f}")
        cmd = "|".join(cmd_parts)

        ok, response = self.request(cmd)
        if not ok:
            return ActionResult.error_result(
                action,
                f"IPC request failed: {response}",
                socket_path=self.socket_path,
                command=cmd,
            )

        if not response:
            return ActionResult.error_result(action, "IPC server returned empty response", command=cmd)

        status_code, server_message = self._parse_response(response)
        if status_code == 0:
            return ActionResult.error_result(
                action,
                server_message or "patrol failed",
                character_id=int(entity_id),
                server_message=server_message,
                command=cmd,
            )

        return ActionResult.ok_result(
            action,
            character_id=int(entity_id),
            waypoint_count=len(waypoints),
            message=server_message,
        )

    def attack_target(self, entity_id: int, target_entity_id: int) -> ActionResult:
        action = "attack_target"
        cmd = "attack|" + str(int(entity_id)) + "|" + str(int(target_entity_id))

        ok, response = self.request(cmd)
        if not ok:
            return ActionResult.error_result(
                action,
                f"IPC request failed: {response}",
                socket_path=self.socket_path,
                command=cmd,
            )

        if not response:
            return ActionResult.error_result(action, "IPC server returned empty response", command=cmd)

        status_code, server_message = self._parse_response(response)
        if status_code == 0:
            return ActionResult.error_result(
                action,
                server_message or "attack failed",
                character_id=int(entity_id),
                target_id=int(target_entity_id),
                server_message=server_message,
                command=cmd,
            )

        return ActionResult.ok_result(
            action,
            character_id=int(entity_id),
            target_id=int(target_entity_id),
            message=server_message,
        )

    def get_state(self, query: str, **filters) -> ActionResult:
        action = "get_state"
        if query != "entities":
            return ActionResult.error_result(action, f"Unsupported query: {query}")

        # Encode filters as key=value segments.
        # Example: state|entities|owner=0|has=move|limit=50
        cmd_parts = ["state", "entities"]
        for k, v in filters.items():
            if v is None:
                continue
            cmd_parts.append(f"{k}={v}")
        cmd = "|".join(cmd_parts)
        ok, response = self.request(cmd)
        if not ok:
            return ActionResult.error_result(
                action,
                f"IPC request failed: {response}",
                socket_path=self.socket_path,
                command=cmd,
            )

        if not response:
            return ActionResult.error_result(action, "IPC server returned empty response", command=cmd)

        status_code, payload = self._parse_response(response)
        if status_code == 0:
            return ActionResult.error_result(action, payload or "state query failed", command=cmd)

        try:
            data = json.loads(payload)
        except Exception as exc:
            return ActionResult.error_result(action, f"Failed to parse JSON state: {exc}", raw=payload)

        return ActionResult.ok_result(action, query=query, filters=dict(filters), state=data)
