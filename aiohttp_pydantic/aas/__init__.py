from importlib import resources
from typing import Iterable, Optional
import json
import jinja2
from aiohttp import web

from .view import get_aas, aas_ui


def _index_j2_content() -> str:
    """
    Returns the content of the index.j2 file in the aiohttp_pydantic.aas package.
    """
    if hasattr(resources, "files"):  # python > 3.8
        with (resources.files("aiohttp_pydantic.aas") / "index.j2").open(
            "r"
        ) as index_file:
            return index_file.read()
    else:
        return resources.read_text("aiohttp_pydantic.aas", "index.j2")


def setup(
    app: web.Application,
    apps_to_expose: Iterable[web.Application] = (),
    url_prefix: str = "/aas",
    enable: bool = True,
    version_spec: Optional[str] = None,
    title_spec: Optional[str] = None,
    security: Optional[dict] = None,
    display_configurations: Optional[dict] = None
):
    if display_configurations is None:
        display_configurations = {}
    if enable:
        aas_app = web.Application()
        # aas_app[key_apps_to_expose] = tuple(apps_to_expose) or (app,)
        aas_app["AAS INDEX TEMPLATE"] = jinja2.Template(_index_j2_content())
        # aas_app[key_version_spec] = version_spec
        # aas_app[key_title_spec] = title_spec
        # aas_app[key_security] = security
        # aas_app[key_display_configurations] = json.dumps(display_configurations)

        aas_app.router.add_get("/spec", get_aas, name="spec")
        aas_app.router.add_get("", aas_ui, name="index")

        app.add_subapp(url_prefix, aas_app)
