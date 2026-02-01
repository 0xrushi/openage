# Copyright 2020-2023 the openage authors. See copying.md for legal info.
#
# pylint: disable=too-many-branches
"""
Mount asset dirs of a game version into the conversion folder.
"""
from __future__ import annotations
import typing


from ....util.fslike.union import Union
from ...value_object.read.media.drs import DRS
from ...value_object.read.media_types import MediaType

if typing.TYPE_CHECKING:
    from openage.convert.value_object.init.game_version import GameVersion
    from openage.util.fslike.directory import Directory


def mount_asset_dirs(
    srcdir: Directory,
    game_version: GameVersion
) -> Union:
    """
    Returns a Union path where srcdir is mounted at /,
    and all the asset files are mounted in subfolders.
    """

    result = Union().root
    result.mount(srcdir)

    def mount_drs(filename: str, target: str) -> None:
        """
        Mounts the DRS file from srcdir's filename at result's target.
        """
        drspath = srcdir[filename]
        result[target].mount(DRS(drspath.open('rb'), game_version).root)

    def mount_aoe2hd_legacy(media_type: MediaType) -> bool:
        """
        Mount legacy AoE2:HD assets that use the classic "Data/" + "Bin/" layout.

        Returns True if something was mounted for the requested media_type.
        """
        mounted_any = False

        legacy_paths: dict[MediaType, list[str]] = {
            MediaType.DATFILE: ["Data/empires2_x1_p1.dat"],
            MediaType.GAMEDATA: ["Data/gamedata_x1_p1.drs"],
            MediaType.GRAPHICS: ["Data/graphics.drs"],
            MediaType.INTERFACE: ["Data/interfac.drs"],
            MediaType.PALETTES: ["Data/interfac.drs"],
            MediaType.SOUNDS: ["Data/sounds.drs", "Data/sounds_x1.drs"],
            # AoE2:HD terrain textures are available as PNGs in Terrain/Textures/.
            # The converter expects files like "g_grs_00_color.png" at the root of the
            # terrain mount point.
            MediaType.TERRAIN: ["Terrain/Textures"],
        }

        for legacy_path in legacy_paths.get(media_type, []):
            path_to_media = srcdir[legacy_path]
            if path_to_media.is_dir():
                result[media_type.value].mount(path_to_media)
                mounted_any = True
                continue

            if not path_to_media.is_file():
                continue

            if path_to_media.suffix.lower() == ".drs":
                mount_drs(legacy_path, media_type.value)
                mounted_any = True
            else:
                # Non-archive files (e.g. .dat) are accessed directly from srcdir.
                mounted_any = True

        return mounted_any

    # Mount the media sources of the game edition
    for media_type, media_paths in game_version.edition.media_paths.items():
        for media_path in media_paths:
            path_to_media = srcdir[media_path]
            if path_to_media.is_dir():
                # Mount folder
                result[media_type.value].mount(path_to_media)

            elif path_to_media.is_file():
                # Mount archive
                if path_to_media.suffix.lower() == ".drs":
                    mount_drs(media_path, media_type.value)

            else:
                if game_version.edition.game_id == "HDEDITION":
                    # Language files are optional and are discovered/loaded separately.
                    if media_type is MediaType.LANGUAGE:
                        continue

                    # Legacy AoE2:HD installs use Data/*.drs instead of resources/_common/drs/*.
                    if mount_aoe2hd_legacy(media_type):
                        continue

                raise FileNotFoundError(f"Media at path {path_to_media} could not be found")

    # Mount the media sources of the game edition
    for expansion in game_version.expansions:
        for media_type, media_paths in expansion.media_paths.items():
            for media_path in media_paths:
                path_to_media = srcdir[media_path]
                if path_to_media.is_dir():
                    # Mount folder
                    result[media_type.value].mount(path_to_media)

                elif path_to_media.is_file():
                    # Mount archive
                    if path_to_media.suffix.lower() == ".drs":
                        mount_drs(media_path, media_type.value)

                else:
                    raise FileNotFoundError(f"Media at path {path_to_media} could not be found")

    return result
