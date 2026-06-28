"""The Asset Library: typed, taggable, searchable, pack-loadable assets.

Everything the platform draws or animates — characters, skeletons, poses,
expressions, animation clips, palettes, props, backgrounds — is an
:class:`Asset` living in an :class:`AssetLibrary`. Assets are addressed by a
stable ``id`` and described by free-form ``tags`` and ``data``. Packs (JSON on
disk) are how thousands of reusable assets are distributed and versioned.
"""

from .base import Asset, ASSET_TYPES
from .library import AssetLibrary
from .pack import AssetPack, load_pack, PackError

__all__ = [
    "Asset",
    "ASSET_TYPES",
    "AssetLibrary",
    "AssetPack",
    "load_pack",
    "PackError",
]
