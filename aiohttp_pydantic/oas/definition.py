"""
Definitions
"""

from typing import Iterable
from aiohttp.web import AppKey, Application


key_apps_to_expose = AppKey("apps to expose", Iterable[Application])
key_index_template = AppKey("index template", str)
key_version_spec = AppKey("version spec", str)
key_title_spec = AppKey("title spec", str)
key_security = AppKey("security", dict)
key_display_configurations = AppKey("key_display_configurations", dict)
key_swagger_ui_version = AppKey("key_swagger_ui_version", str)


__all__ = [
    "key_apps_to_expose",
    "key_display_configurations",
    "key_index_template",
    "key_security",
    "key_swagger_ui_version",
    "key_title_spec",
    "key_version_spec",
]
