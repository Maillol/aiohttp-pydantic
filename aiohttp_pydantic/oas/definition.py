"""
Definitions
"""

from typing import Iterable

import aiohttp
from aiohttp import web
from packaging.version import Version

AIOHTTP_HAS_APP_KEY: bool = Version(aiohttp.__version__) >= Version("3.9.0b0")


if AIOHTTP_HAS_APP_KEY:
    from aiohttp.web import AppKey
else:

    def AppKey(key_name: str, _) -> str:
        return key_name


key_apps_to_expose = web.AppKey("apps to expose", Iterable[web.Application])
key_index_template = web.AppKey("index template", str)
key_version_spec = web.AppKey("version spec", str)
key_title_spec = web.AppKey("title spec", str)
key_security = web.AppKey("security", dict)
key_display_configurations = web.AppKey("key_display_configurations", dict)

__all__ = [
    key_apps_to_expose,
    key_index_template,
    key_version_spec,
    key_title_spec,
    key_security,
    key_display_configurations
]
