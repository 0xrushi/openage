# Copyright 2026-2026 the openage authors. See copying.md for legal info.

"""Agent-like dispatcher for intent-level game control."""

from __future__ import annotations

from typing import Any, Dict

from . import catalog
from .ipc import IpcClient
from .schema import ACTIONS, ActionResult, Position


class OpenAgeAgent:
    """A small intent dispatcher.

    Only spawning is implemented (via engine IPC). Other actions are present as
    API surface and return supported=False.
    """

    def __init__(
        self,
        socket_path: str = "/tmp/openage_spawn.sock",
        timeout_s: float = 2.0,
    ):
        self._ipc = IpcClient(socket_path=socket_path, timeout_s=timeout_s)

        # Local, agent-side state.
        self._spawn_history = []  # list[int]
        self._entities_by_tag = {}  # dict[str, int]
        self._selected_id = None  # Optional[int]

    def list_actions(self):
        return list(ACTIONS)

    def capabilities(self) -> Dict[str, bool]:
        return {
            "spawn_character": True,
            "switch_active_character": False,
            "select_character": False,
            "move_character": True,
            "list_unit_types": True,
            "resolve_unit_type": True,
        }

    def act(self, name: str, **kwargs: Any) -> ActionResult:
        if name == "spawn_character":
            return self._spawn_character(**kwargs)

        if name == "select_character":
            return self._select_character(**kwargs)

        if name == "move_character":
            return self._move_character(**kwargs)

        if name == "list_unit_types":
            return ActionResult.ok_result(name, unit_types=catalog.list_unit_types())

        if name == "resolve_unit_type":
            entity_type = kwargs.get("entity_type")
            try:
                resolved = catalog.resolve_entity_type(str(entity_type))
            except Exception as exc:
                return ActionResult.error_result(name, str(exc))
            return ActionResult.ok_result(name, nyan_entity=resolved)

        # Stubs (present but unsupported).
        if name == "switch_active_character":
            return ActionResult.not_supported(
                name,
                "Action not supported yet (requires additional engine IPC commands)",
            )

        return ActionResult.error_result(name, f"Unknown action: {name}")

    def _spawn_character(
        self,
        entity_type: str,
        position: Any,
        owner: int = 0,
        tag: str | None = None,
    ) -> ActionResult:
        try:
            nyan_entity = catalog.resolve_entity_type(entity_type)
            pos = Position.from_obj(position)
        except Exception as exc:
            return ActionResult.error_result("spawn_character", str(exc))

        res = self._ipc.spawn(nyan_entity=nyan_entity, owner=owner, pos=pos)
        if res.ok:
            entity_id = res.data.get("entity_id")
            if isinstance(entity_id, int):
                self._spawn_history.append(entity_id)
                self._selected_id = entity_id
                if tag:
                    self._entities_by_tag[str(tag)] = entity_id
            return ActionResult.ok_result(
                res.action,
                **res.data,
                tag=(str(tag) if tag else None),
            )

        return res

    def _resolve_character_id(
        self,
        character_id: Any = None,
        tag: Any = None,
        spawn_index: Any = None,
        default_to_selected: bool = False,
    ) -> tuple[int | None, str | None]:
        """Resolve a target entity id from multiple addressing modes."""

        if character_id is not None:
            try:
                return int(character_id), "character_id"
            except Exception as exc:
                raise TypeError("character_id must be an int") from exc

        if tag is not None:
            key = str(tag)
            if key in self._entities_by_tag:
                return self._entities_by_tag[key], "tag"
            raise ValueError(f"Unknown tag '{key}'. Known tags: {sorted(self._entities_by_tag.keys())}")

        if spawn_index is not None:
            try:
                idx = int(spawn_index)
            except Exception as exc:
                raise TypeError("spawn_index must be an int") from exc
            if not self._spawn_history:
                raise ValueError("No spawned entities recorded yet")
            try:
                return self._spawn_history[idx], "spawn_index"
            except IndexError as exc:
                raise ValueError(f"spawn_index {idx} out of range for {len(self._spawn_history)} spawns") from exc

        if default_to_selected:
            return self._selected_id, "selected"

        return None, None

    def _select_character(self, character_id: Any = None, tag: Any = None, spawn_index: Any = None) -> ActionResult:
        try:
            entity_id, mode = self._resolve_character_id(
                character_id=character_id,
                tag=tag,
                spawn_index=spawn_index,
                default_to_selected=False,
            )
        except Exception as exc:
            return ActionResult.error_result("select_character", str(exc))

        if entity_id is None:
            return ActionResult.error_result(
                "select_character",
                "No selector provided; pass character_id, tag, or spawn_index",
            )

        self._selected_id = entity_id
        return ActionResult.ok_result("select_character", character_id=entity_id, resolved_by=mode)

    def _move_character(self, destination: Any, character_id: Any = None, tag: Any = None, spawn_index: Any = None) -> ActionResult:
        try:
            dest = Position.from_obj(destination)
            entity_id, mode = self._resolve_character_id(
                character_id=character_id,
                tag=tag,
                spawn_index=spawn_index,
                default_to_selected=True,
            )
        except Exception as exc:
            return ActionResult.error_result("move_character", str(exc))

        if entity_id is None:
            return ActionResult.error_result(
                "move_character",
                "No character selected; pass character_id/tag/spawn_index or call select_character first",
            )

        res = self._ipc.move(entity_id=entity_id, destination=dest)
        if res.ok:
            # Keep selection; moving implies the caller is operating on this entity.
            self._selected_id = entity_id
            return ActionResult.ok_result(
                res.action,
                **res.data,
                resolved_by=mode,
                destination={"ne": dest.ne, "se": dest.se, "up": dest.up},
            )

        # Add resolution context for failures too.
        return ActionResult.error_result(
            "move_character",
            res.error or "move failed",
            **res.data,
            resolved_by=mode,
            destination={"ne": dest.ne, "se": dest.se, "up": dest.up},
        )
