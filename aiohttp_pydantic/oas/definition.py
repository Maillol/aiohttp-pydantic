"""
Definitions
"""

from typing import Iterable
from aiohttp import web
from ..compat import AppKey


key_apps_to_expose = AppKey("apps to expose", Iterable[web.Application])
key_index_template = AppKey("index template", str)
key_version_spec = AppKey("version spec", str)
key_title_spec = AppKey("title spec", str)
key_security = AppKey("security", dict)
key_display_configurations = AppKey("key_display_configurations", dict)


__all__ = [
    key_apps_to_expose,
    key_index_template,
    key_version_spec,
    key_title_spec,
    key_security,
    key_display_configurations
]
