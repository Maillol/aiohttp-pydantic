"""
Compatibility aiohttp version.
"""

import aiohttp
from packaging.version import Version

AIOHTTP_HAS_APP_KEY: bool = Version(aiohttp.__version__) >= Version("3.9.0b0")


if AIOHTTP_HAS_APP_KEY:
    from aiohttp.web import AppKey
else:
    def AppKey(key_name: str, _) -> str:
        return key_name


__all__ = ("AppKey",)
