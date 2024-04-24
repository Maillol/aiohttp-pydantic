"""
Definitions
"""

from aiohttp import web

key_apps_to_expose = web.AppKey("apps to expose")
key_index_template = web.AppKey("index template")
key_version_spec = web.AppKey("version spec")
key_title_spec = web.AppKey("title spec")

__all__ = [
    key_apps_to_expose,
    key_index_template,
    key_version_spec,
    key_title_spec,
]
