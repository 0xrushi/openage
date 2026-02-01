# Copyright 2024-2024 © openage authors. See copying.md for legal info.

from libc.stdint cimport uint64_t

cdef extern:
    uint64_t openage_python_spawn_unit(const char *, uint64_t, double, double, double)
    int openage_is_game_active()

def spawn_unit(str nyan_entity, int owner=0, double ne=5.0, double se=5.0, double up=0.0):
    if not is_game_active():
        raise RuntimeError("No game is currently running.")

    cdef bytes nyan_entity_bytes = nyan_entity.encode("utf-8")
    cdef char *nyan_entity_cpp = nyan_entity_bytes
    cdef uint64_t owner_id = <uint64_t> owner
    cdef uint64_t entity_id

    entity_id = openage_python_spawn_unit(nyan_entity_cpp, owner_id, ne, se, up)

    if entity_id == 0:
        raise RuntimeError("Failed to spawn unit.")

    return int(entity_id)

def is_game_active():
    return openage_is_game_active() != 0
