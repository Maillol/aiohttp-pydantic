from importlib import resources
from typing import Iterable, Optional

import jinja2
from aiohttp import web
from swagger_ui_bundle import swagger_ui_path

from .view import get_oas, oas_ui


def setup(
    app: web.Application,
    apps_to_expose: Iterable[web.Application] = (),
    url_prefix: str = "/oas",
    enable: bool = True,
    version_spec: Optional[str] = None,
    title_spec: Optional[str] = None,
):
    if enable:
        oas_app = web.Application()
        oas_app["apps to expose"] = tuple(apps_to_expose) or (app,)
        oas_app["index template"] = jinja2.Template(
            resources.read_text("aiohttp_pydantic.oas", "index.j2")
        )
        oas_app["version_spec"] = version_spec
        oas_app["title_spec"] = title_spec

        oas_app.router.add_get("/spec", get_oas, name="spec")
        oas_app.router.add_static("/static", swagger_ui_path, name="static")
        oas_app.router.add_get("", oas_ui, name="index")

        app.add_subapp(url_prefix, oas_app)
