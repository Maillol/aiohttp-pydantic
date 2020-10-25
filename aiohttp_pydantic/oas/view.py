from aiohttp.web import json_response, Response

from aiohttp_pydantic.oas.struct import OpenApiSpec3, OperationObject, PathItem
from typing import Type

from ..injectors import _parse_func_signature
from ..view import PydanticView, is_pydantic_view


JSON_SCHEMA_TYPES = {float: "number", str: "string", int: "integer"}


def _add_http_method_to_oas(oas_path: PathItem, method: str, view: Type[PydanticView]):
    method = method.lower()
    mtd: OperationObject = getattr(oas_path, method)
    handler = getattr(view, method)
    path_args, body_args, qs_args, header_args = _parse_func_signature(handler)

    if body_args:
        mtd.request_body.content = {
            "application/json": {"schema": next(iter(body_args.values())).schema()}
        }

    i = 0
    for i, (name, type_) in enumerate(path_args.items()):
        mtd.parameters[i].required = True
        mtd.parameters[i].in_ = "path"
        mtd.parameters[i].name = name
        mtd.parameters[i].schema = {"type": JSON_SCHEMA_TYPES[type_]}

    for i, (name, type_) in enumerate(qs_args.items(), i + 1):
        mtd.parameters[i].required = False
        mtd.parameters[i].in_ = "query"
        mtd.parameters[i].name = name
        mtd.parameters[i].schema = {"type": JSON_SCHEMA_TYPES[type_]}

    for i, (name, type_) in enumerate(header_args.items(), i + 1):
        mtd.parameters[i].required = False
        mtd.parameters[i].in_ = "header"
        mtd.parameters[i].name = name
        mtd.parameters[i].schema = {"type": JSON_SCHEMA_TYPES[type_]}


async def get_oas(request):
    """
    Generate Open Api Specification from PydanticView in application.
    """
    apps = request.app["apps to expose"]
    oas = OpenApiSpec3()
    for app in apps:
        for resources in app.router.resources():
            for resource_route in resources:
                if is_pydantic_view(resource_route.handler):
                    view: Type[PydanticView] = resource_route.handler
                    info = resource_route.get_info()
                    path = oas.paths[info.get("path", info.get("formatter"))]
                    if resource_route.method == "*":
                        for method_name in view.allowed_methods:
                            _add_http_method_to_oas(path, method_name, view)
                    else:
                        _add_http_method_to_oas(path, resource_route.method, view)

    return json_response(oas.spec)


async def oas_ui(request):
    """
    View to serve the swagger-ui to read open api specification of application.
    """
    template = request.app["index template"]

    static_url = request.app.router["static"].url_for(filename="")
    spec_url = request.app.router["spec"].url_for()
    host = request.url.origin()

    return Response(
        text=template.render(
            {
                "openapi_spec_url": host.with_path(str(spec_url)),
                "static_url": host.with_path(str(static_url)),
            }
        ),
        content_type="text/html",
        charset="utf-8",
    )
