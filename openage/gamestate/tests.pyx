# Copyright 2023-2023 the openage authors. See copying.md for legal info.

"""
tests for the games simulation.
"""

import argparse

from libcpp.string cimport string
from libcpp.vector cimport vector
from libc.stdint cimport uint64_t

from libopenage.util.path cimport Path as Path_cpp
from libopenage.pyinterface.pyobject cimport PyObj
from cpython.ref cimport PyObject
from libopenage.gamestate.demo.tests cimport simulation_demo as simulation_demo_c
from libopenage.gamestate.demo.tests cimport spawn_nyan_entity as spawn_nyan_entity_c


def spawn_entity(
    str nyan_entity,
    list modpacks = None,
    int owner = 0,
    double ne = 5.0,
    double se = 5.0,
    double up = 0.0,
    str asset_dir = None,
    str cfg_dir = None,
):
    """
    Spawn a nyan entity into a minimal gamestate and return its numeric entity id.

    Note: This creates a temporary simulation and exits right away. It's intended for
    scripting/experiments, not (yet) for controlling the main game instance.
    """
    # When called outside of the normal openage entrypoints (e.g. from a standalone
    # python script), we must initialize the C++<->Python interface first.
    #
    # openage's main entrypoints already do this, so this is effectively a no-op there.
    from argparse import Namespace
    from ..cppinterface.setup import setup as cpp_interface_setup
    cpp_interface_setup(Namespace(trap_exceptions=False))

    from ..cvar.location import get_config_path
    from ..assets import get_asset_path
    from ..util.fslike.union import Union

    root = Union().root
    root["assets"].mount(get_asset_path(asset_dir))
    root["cfg"].mount(get_config_path(cfg_dir))

    cdef Path_cpp root_cpp = Path_cpp(PyObj(<PyObject*>root.fsobj),
                                  root.parts)

    cdef vector[string] modpacks_vec
    if modpacks is not None:
        for modpack in modpacks:
            modpacks_vec.push_back(str(modpack).encode("utf-8"))

    cdef string nyan_entity_cpp = nyan_entity.encode("utf-8")
    cdef uint64_t owner_id = <uint64_t> owner
    cdef uint64_t entity_id

    with nogil:
        entity_id = spawn_nyan_entity_c(root_cpp,
                                        modpacks_vec,
                                        nyan_entity_cpp,
                                        owner_id,
                                        ne,
                                        se,
                                        up)

    return int(entity_id)


def simulation_demo(list argv):
    """
    invokes the available simulation demos.
    """

    cmd = argparse.ArgumentParser(
        prog='... simulation_demo',
        description='Demo of the game simulation')
    cmd.add_argument("test_id", type=int, help="id of the demo to run.")
    cmd.add_argument("--asset-dir",
                         help="Use this as an additional asset directory.")
    cmd.add_argument("--cfg-dir",
                         help="Use this as an additional config directory.")

    args = cmd.parse_args(argv)

    from ..cvar.location import get_config_path
    from ..assets import get_asset_path
    from ..util.fslike.union import Union

    # create virtual file system for data paths
    root = Union().root

    # mount the assets folder union at "assets/"
    root["assets"].mount(get_asset_path(args.asset_dir))

    # mount the config folder at "cfg/"
    root["cfg"].mount(get_config_path(args.cfg_dir))

    cdef int simulation_test_id = args.test_id

    cdef Path_cpp root_cpp = Path_cpp(PyObj(<PyObject*>root.fsobj),
                                  root.parts)

    with nogil:
        simulation_demo_c(simulation_test_id, root_cpp)


def spawn_nyan_entity(list argv):
    """
    Spawn a nyan entity from Python for quick experiments.

    Example:
      ./run test --demo gamestate.tests.spawn_nyan_entity -- \
        --modpack hd_base \
        --nyan-entity hd_base.data.game_entity.generic.villager.villager.Villager \
        --ne 5 --se 5
    """
    cmd = argparse.ArgumentParser(
        prog='... spawn_nyan_entity',
        description='Spawn a nyan entity into a minimal gamestate and exit')
    cmd.add_argument("--asset-dir",
                         help="Use this as an additional asset directory.")
    cmd.add_argument("--cfg-dir",
                         help="Use this as an additional config directory.")
    cmd.add_argument("--modpack", action="append", default=[],
                     help="Modpack(s) to load (e.g. hd_base). Can be used multiple times.")
    cmd.add_argument("--nyan-entity", required=True,
                     help="Fully qualified nyan object name (fqon) to spawn.")
    cmd.add_argument("--owner", type=int, default=0, help="Owner player id (default: 0).")
    cmd.add_argument("--ne", type=float, default=5.0, help="Spawn position NE coordinate.")
    cmd.add_argument("--se", type=float, default=5.0, help="Spawn position SE coordinate.")
    cmd.add_argument("--up", type=float, default=0.0, help="Spawn position UP coordinate.")

    args = cmd.parse_args(argv)

    return spawn_entity(
        args.nyan_entity,
        modpacks=args.modpack,
        owner=args.owner,
        ne=args.ne,
        se=args.se,
        up=args.up,
        asset_dir=args.asset_dir,
        cfg_dir=args.cfg_dir,
    )
