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
        timeout_s: float = 8.0,
    ):
        self._ipc = IpcClient(socket_path=socket_path, timeout_s=timeout_s)

        # Local, agent-side state.
        self._spawn_history = []  # list[int]
        self._entities_by_tag = {}  # dict[str, int]
        self._selected_id = None  # Optional[int]
        self._groups = {}  # dict[str, list[int]]

    def list_actions(self):
        return list(ACTIONS)

    def capabilities(self) -> Dict[str, bool]:
        return {
            "get_state": True,
            "spawn_character": True,
            "switch_active_character": False,
            "select_character": False,
            "select_by_query": True,
            "move_character": True,
            "stop_character": True,
            "patrol": True,
            "attack_target": True,
            "list_unit_types": True,
            "resolve_unit_type": True,
            "create_group": True,
            "get_group": True,
            "disband_group": True,
            "command_group": True,
        }

    def act(self, name: str, **kwargs: Any) -> ActionResult:
        if name == "get_state":
            query = kwargs.pop("query", "entities")
            return self._ipc.get_state(str(query), **kwargs)

        if name == "spawn_character":
            return self._spawn_character(**kwargs)

        if name == "select_character":
            return self._select_character(**kwargs)

        if name == "select_by_query":
            return self._select_by_query(**kwargs)

        if name == "move_character":
            return self._move_character(**kwargs)

        if name == "stop_character":
            return self._stop_character(**kwargs)

        if name == "patrol":
            return self._patrol(**kwargs)

        if name == "attack_target":
            return self._attack_target(**kwargs)

        if name == "create_group":
            return self._create_group(**kwargs)

        if name == "get_group":
            return self._get_group(**kwargs)

        if name == "disband_group":
            return self._disband_group(**kwargs)

        if name == "command_group":
            return self._command_group(**kwargs)

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

    def _select_by_query(
        self,
        owner: Any = None,
        has: Any = None,
        limit: Any = 50,
        strategy: Any = "nearest",
        near: Any = None,
    ) -> ActionResult:
        action = "select_by_query"
        try:
            strategy_s = str(strategy)
            if limit is not None:
                limit_i = int(limit)
            else:
                limit_i = None
        except Exception as exc:
            return ActionResult.error_result(action, str(exc))

        state_res = self._ipc.get_state(
            "entities",
            owner=owner,
            has=has,
            limit=limit_i,
        )
        if not state_res.ok:
            return ActionResult.error_result(action, state_res.error or "state query failed", **state_res.data)

        state = state_res.data.get("state")
        entities = (state or {}).get("entities", []) if isinstance(state, dict) else []
        if not entities:
            return ActionResult.error_result(action, "No entities matched query", **state_res.data)

        chosen = None
        resolved_by = "first"

        if strategy_s == "first":
            chosen = entities[0]
        elif strategy_s == "nearest":
            if near is None:
                return ActionResult.error_result(action, "near is required for strategy='nearest'")
            ref = Position.from_obj(near)
            best_d2 = None
            for ent in entities:
                if not isinstance(ent, dict):
                    continue
                pos = ent.get("pos")
                if not isinstance(pos, dict):
                    continue
                ne = float(pos.get("ne", 0.0))
                se = float(pos.get("se", 0.0))
                up = float(pos.get("up", 0.0))
                d2 = (ne - ref.ne) ** 2 + (se - ref.se) ** 2 + (up - ref.up) ** 2
                if best_d2 is None or d2 < best_d2:
                    best_d2 = d2
                    chosen = ent
            resolved_by = "nearest"
        else:
            return ActionResult.error_result(action, f"Unknown strategy: {strategy_s}")

        if not isinstance(chosen, dict) or "id" not in chosen:
            return ActionResult.error_result(action, "Failed to resolve selection")

        try:
            entity_id = int(chosen["id"])
        except Exception as exc:
            return ActionResult.error_result(action, f"Invalid entity id in state: {exc}")

        self._selected_id = entity_id
        return ActionResult.ok_result(
            action,
            character_id=entity_id,
            resolved_by=resolved_by,
            candidate_count=len(entities),
        )

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

    def _stop_character(self, character_id: Any = None, tag: Any = None, spawn_index: Any = None) -> ActionResult:
        try:
            entity_id, mode = self._resolve_character_id(
                character_id=character_id,
                tag=tag,
                spawn_index=spawn_index,
                default_to_selected=True,
            )
        except Exception as exc:
            return ActionResult.error_result("stop_character", str(exc))

        if entity_id is None:
            return ActionResult.error_result(
                "stop_character",
                "No character selected; pass character_id/tag/spawn_index or call select_character first",
            )

        res = self._ipc.stop(entity_id=entity_id)
        if res.ok:
            self._selected_id = entity_id
            return ActionResult.ok_result(res.action, **res.data, resolved_by=mode)

        return ActionResult.error_result("stop_character", res.error or "stop failed", **res.data, resolved_by=mode)

    def _patrol(self, waypoints: Any, character_id: Any = None, tag: Any = None, spawn_index: Any = None) -> ActionResult:
        action = "patrol"
        try:
            if not isinstance(waypoints, (list, tuple)) or len(waypoints) < 1:
                return ActionResult.error_result(action, "waypoints must be a non-empty list of positions")
            positions = [Position.from_obj(wp) for wp in waypoints]
            entity_id, mode = self._resolve_character_id(
                character_id=character_id,
                tag=tag,
                spawn_index=spawn_index,
                default_to_selected=True,
            )
        except Exception as exc:
            return ActionResult.error_result(action, str(exc))

        if entity_id is None:
            return ActionResult.error_result(
                action,
                "No character selected; pass character_id/tag/spawn_index or call select_character first",
            )

        res = self._ipc.patrol(entity_id=entity_id, waypoints=positions)
        if res.ok:
            self._selected_id = entity_id
            return ActionResult.ok_result(
                action,
                **res.data,
                resolved_by=mode,
                waypoints=[{"ne": p.ne, "se": p.se, "up": p.up} for p in positions],
            )

        return ActionResult.error_result(action, res.error or "patrol failed", **res.data, resolved_by=mode)

    def _attack_target(
        self,
        target: Any,
        character_id: Any = None,
        tag: Any = None,
        spawn_index: Any = None,
    ) -> ActionResult:
        action = "attack_target"
        try:
            target_id = int(target)
        except (TypeError, ValueError) as exc:
            return ActionResult.error_result(action, f"target must be an entity id (int): {exc}")

        try:
            entity_id, mode = self._resolve_character_id(
                character_id=character_id,
                tag=tag,
                spawn_index=spawn_index,
                default_to_selected=True,
            )
        except Exception as exc:
            return ActionResult.error_result(action, str(exc))

        if entity_id is None:
            return ActionResult.error_result(
                action,
                "No character selected; pass character_id/tag/spawn_index or call select_character first",
            )

        res = self._ipc.attack_target(entity_id=entity_id, target_entity_id=target_id)
        if res.ok:
            self._selected_id = entity_id
            return ActionResult.ok_result(
                action,
                **res.data,
                resolved_by=mode,
            )

        return ActionResult.error_result(
            action,
            res.error or "attack failed",
            **res.data,
            resolved_by=mode,
        )

    def _create_group(
        self,
        group_id: Any,
        character_ids: Any = None,
        tags: Any = None,
        spawn_indices: Any = None,
    ) -> ActionResult:
        action = "create_group"
        key = str(group_id)
        ids = []

        if character_ids is not None:
            if not isinstance(character_ids, (list, tuple)):
                return ActionResult.error_result(action, "character_ids must be a list")
            for cid in character_ids:
                try:
                    ids.append(int(cid))
                except (TypeError, ValueError) as exc:
                    return ActionResult.error_result(action, f"Invalid character_id: {exc}")

        if tags is not None:
            if not isinstance(tags, (list, tuple)):
                return ActionResult.error_result(action, "tags must be a list")
            for tag in tags:
                tag_s = str(tag)
                if tag_s not in self._entities_by_tag:
                    return ActionResult.error_result(
                        action,
                        f"Unknown tag '{tag_s}'. Known tags: {sorted(self._entities_by_tag.keys())}",
                    )
                ids.append(self._entities_by_tag[tag_s])

        if spawn_indices is not None:
            if not isinstance(spawn_indices, (list, tuple)):
                return ActionResult.error_result(action, "spawn_indices must be a list")
            for idx in spawn_indices:
                try:
                    idx_i = int(idx)
                except (TypeError, ValueError) as exc:
                    return ActionResult.error_result(action, f"Invalid spawn_index: {exc}")
                if not self._spawn_history:
                    return ActionResult.error_result(action, "No spawned entities recorded yet")
                try:
                    ids.append(self._spawn_history[idx_i])
                except IndexError:
                    return ActionResult.error_result(
                        action,
                        f"spawn_index {idx_i} out of range for {len(self._spawn_history)} spawns",
                    )

        if not ids:
            return ActionResult.error_result(action, "No members specified; pass character_ids, tags, or spawn_indices")

        # Deduplicate while preserving order.
        seen = set()
        unique = []
        for eid in ids:
            if eid not in seen:
                seen.add(eid)
                unique.append(eid)

        self._groups[key] = unique
        return ActionResult.ok_result(action, group_id=key, member_count=len(unique), members=unique)

    def _get_group(self, group_id: Any) -> ActionResult:
        action = "get_group"
        key = str(group_id)
        if key not in self._groups:
            return ActionResult.error_result(
                action,
                f"Unknown group '{key}'. Known groups: {sorted(self._groups.keys())}",
            )
        members = self._groups[key]
        return ActionResult.ok_result(action, group_id=key, member_count=len(members), members=list(members))

    def _disband_group(self, group_id: Any) -> ActionResult:
        action = "disband_group"
        key = str(group_id)
        if key not in self._groups:
            return ActionResult.error_result(
                action,
                f"Unknown group '{key}'. Known groups: {sorted(self._groups.keys())}",
            )
        members = self._groups.pop(key)
        return ActionResult.ok_result(action, group_id=key, disbanded_count=len(members))

    def _command_group(self, group_id: Any, action: Any, **kwargs: Any) -> ActionResult:
        meta_action = "command_group"
        key = str(group_id)
        action_s = str(action)

        if key not in self._groups:
            return ActionResult.error_result(
                meta_action,
                f"Unknown group '{key}'. Known groups: {sorted(self._groups.keys())}",
            )

        allowed = {"move_character", "stop_character", "patrol", "attack_target"}
        if action_s not in allowed:
            return ActionResult.error_result(
                meta_action,
                f"Unsupported group action '{action_s}'. Allowed: {sorted(allowed)}",
            )

        members = self._groups[key]
        if not members:
            return ActionResult.error_result(meta_action, "Group is empty")

        results = []
        ok_count = 0
        fail_count = 0

        for entity_id in members:
            res = self.act(action_s, character_id=entity_id, **kwargs)
            results.append({"character_id": entity_id, "ok": res.ok, "error": res.error})
            if res.ok:
                ok_count += 1
            else:
                fail_count += 1

        all_ok = fail_count == 0
        if all_ok:
            return ActionResult.ok_result(
                meta_action,
                group_id=key,
                group_action=action_s,
                ok_count=ok_count,
                fail_count=fail_count,
                results=results,
            )
        return ActionResult.error_result(
            meta_action,
            f"{fail_count}/{len(members)} commands failed",
            group_id=key,
            group_action=action_s,
            ok_count=ok_count,
            fail_count=fail_count,
            results=results,
        )
