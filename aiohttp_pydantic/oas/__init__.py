from importlib import resources
from typing import Iterable, Optional
import json
import jinja2
from aiohttp import web
from swagger_ui_bundle import swagger_ui_path

from .view import get_oas, oas_ui
from .definition import (
    key_apps_to_expose,
    key_index_template,
    key_version_spec,
    key_title_spec,
    key_security,
    key_display_configurations,
)


def _index_j2_content() -> str:
    """
    Returns the content of the index.j2 file in the aiohttp_pydantic.oas package.
    """
    if hasattr(resources, "files"):  # python > 3.8
        with (resources.files("aiohttp_pydantic.oas") / "index.j2").open(
            "r"
        ) as index_file:
            return index_file.read()
    else:
        return resources.read_text("aiohttp_pydantic.oas", "index.j2")


def setup(
    app: web.Application,
    apps_to_expose: Iterable[web.Application] = (),
    url_prefix: str = "/oas",
    enable: bool = True,
    version_spec: Optional[str] = None,
    title_spec: Optional[str] = None,
    security: Optional[dict] = None,
    display_configurations: Optional[dict] = None
):
    if display_configurations is None:
        display_configurations = {}
    if enable:
        oas_app = web.Application()
        oas_app[key_apps_to_expose] = tuple(apps_to_expose) or (app,)
        oas_app[key_index_template] = jinja2.Template(_index_j2_content())
        oas_app[key_version_spec] = version_spec
        oas_app[key_title_spec] = title_spec
        oas_app[key_security] = security
        oas_app[key_display_configurations] = json.dumps(display_configurations)

        oas_app.router.add_get("/spec", get_oas, name="spec")
        oas_app.router.add_static("/static", swagger_ui_path, name="static")
        oas_app.router.add_get("", oas_ui, name="index")

        app.add_subapp(url_prefix, oas_app)
