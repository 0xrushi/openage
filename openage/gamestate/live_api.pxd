# Copyright 2024-2024 the openage authors. See copying.md for legal info.

from libopenage.gamestate.simulation cimport GameSimulation
from libopenage.gamestate.global_simulation cimport GlobalSimulation


cdef extern from "openage/gamestate/global_simulation.h" namespace "openage":
    GlobalSimulation &global_simulation() except +
