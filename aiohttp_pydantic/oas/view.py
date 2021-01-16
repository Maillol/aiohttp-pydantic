import typing
from inspect import getdoc
from itertools import count
from typing import List, Type

from aiohttp.web import Response, json_response
from aiohttp.web_app import Application
from pydantic import BaseModel

from aiohttp_pydantic.oas.struct import OpenApiSpec3, OperationObject, PathItem, Link
from . import docstring_parser

from ..injectors import _parse_func_signature
from ..utils import is_pydantic_base_model
from ..view import PydanticView, is_pydantic_view
from .typing import is_status_code_type


def _handle_optional(type_):
    """
    Returns the type wrapped in Optional or None.
    >>>  from typing import Optional
    >>>  _handle_optional(int)
    >>>  _handle_optional(Optional[str])
    <class 'str'>
    """
    if typing.get_origin(type_) is typing.Union:
        args = typing.get_args(type_)
        if len(args) == 2 and type(None) in args:
            return next(iter(set(args) - {type(None)}))
    return None


class LinksBuilder:
    def __init__(self):
        self._links = {}
        self._parameters = {}

    def add_src_parameter(self, link: Link, parameter_type, parameter_path):
        """
        parameter_type: must be a typing.NewType.
        parameter_path: example: "$response.body#/id"
        """
        self._links.setdefault(link, []).append((parameter_type, parameter_path))

    def add_destination_parameter(self, parameter_type, operation_id, parameter_name):
        """
        parameter_type: must be a typing.NewType.
        parameter_name: The name of parameter.
        """
        self._parameters.setdefault(parameter_type, []).append(
            {"operation_id": operation_id, "parameter_name": parameter_name}
        )

    def build_links(self):
        link: Link
        for link, type_and_paths in self._links.items():
            for (parameter_type, parameter_path) in type_and_paths:
                for parameter in self._parameters[parameter_type]:
                    link.operation_id = parameter["operation_id"]
                    link.parameters[parameter["parameter_name"]] = parameter_path


class _OASResponseBuilder:
    """
    Parse the type annotated as returned by a function and
    generate the OAS operation response.
    """

    def __init__(
        self,
        oas: OpenApiSpec3,
        oas_operation: OperationObject,
        status_code_descriptions,
        links_builder,
    ):
        self._oas_operation = oas_operation
        self._oas = oas
        self._status_code_descriptions = status_code_descriptions
        self._current_status_code = None
        self._links_builder: LinksBuilder = links_builder

    def _handle_pydantic_base_model(self, obj):
        if is_pydantic_base_model(obj):
            response_schema = obj.schema(ref_template="#/components/schemas/{model}")
            if def_sub_schemas := response_schema.pop("definitions", None):
                self._oas.components.schemas.update(def_sub_schemas)

            for field_name, field_type in obj.__annotations__.items():
                if hasattr(field_type, "__supertype__"):
                    oas_link = self._oas_operation.responses[
                        self._current_status_code
                    ].links[
                        "link_name"
                    ]  # TODO: Generate a link name.
                    self._links_builder.add_src_parameter(
                        oas_link, field_type, f"$response.body#/{field_name}"
                    )
            return response_schema
        return {}

    def _handle_list(self, obj):
        if typing.get_origin(obj) is list:
            return {
                "type": "array",
                "items": self._handle_pydantic_base_model(typing.get_args(obj)[0]),
            }
        return self._handle_pydantic_base_model(obj)

    def _handle_status_code_type(self, obj):
        if is_status_code_type(typing.get_origin(obj)):
            status_code = typing.get_origin(obj).__name__[1:]
            self._current_status_code = status_code
            self._oas_operation.responses[status_code].content = {
                "application/json": {
                    "schema": self._handle_list(typing.get_args(obj)[0])
                }
            }
            desc = self._status_code_descriptions.get(int(status_code))
            if desc:
                self._oas_operation.responses[status_code].description = desc

        elif is_status_code_type(obj):
            status_code = obj.__name__[1:]
            self._current_status_code = status_code
            self._oas_operation.responses[status_code].content = {}
            desc = self._status_code_descriptions.get(int(status_code))
            if desc:
                self._oas_operation.responses[status_code].description = desc

    def _handle_union(self, obj):
        if typing.get_origin(obj) is typing.Union:
            for arg in typing.get_args(obj):
                self._handle_status_code_type(arg)
        self._handle_status_code_type(obj)

    def build(self, obj):
        self._handle_union(obj)


def _add_http_method_to_oas(
    oas: OpenApiSpec3,
    oas_path: PathItem,
    http_method: str,
    view: Type[PydanticView],
    links_builder: LinksBuilder,
):
    http_method = http_method.lower()
    oas_operation: OperationObject = getattr(oas_path, http_method)
    handler = getattr(view, http_method)
    path_args, body_args, qs_args, header_args, defaults = _parse_func_signature(
        handler
    )
    description = getdoc(handler)
    if description:
        oas_operation.description = docstring_parser.operation(description)
        status_code_descriptions = docstring_parser.status_code(description)
    else:
        status_code_descriptions = {}

    if body_args:
        body_schema = next(iter(body_args.values())).schema(
            ref_template="#/components/schemas/{model}"
        )
        if def_sub_schemas := body_schema.pop("definitions", None):
            oas.components.schemas.update(def_sub_schemas)

        oas_operation.request_body.content = {
            "application/json": {"schema": body_schema}
        }

    indexes = count()
    for args_location, args in (
        ("path", path_args.items()),
        ("query", qs_args.items()),
        ("header", header_args.items()),
    ):
        for name, type_ in args:
            i = next(indexes)
            oas_operation.parameters[i].in_ = args_location
            oas_operation.parameters[i].name = name
            optional_type = _handle_optional(type_)

            attrs = {"__annotations__": {"__root__": type_}}
            if name in defaults:
                attrs["__root__"] = defaults[name]

            oas_operation.parameters[i].schema = type(name, (BaseModel,), attrs).schema(
                ref_template="#/components/schemas/{model}"
            )

            oas_operation.parameters[i].required = optional_type is None

            linked_parameter = type_ if optional_type is None else optional_type
            if hasattr(linked_parameter, "__supertype__"):
                links_builder.add_destination_parameter(
                    linked_parameter,
                    f"{handler.__module__}.{handler.__qualname__}",
                    name,
                )

    return_type = handler.__annotations__.get("return")
    if return_type is not None:
        _OASResponseBuilder(
            oas, oas_operation, status_code_descriptions, links_builder
        ).build(return_type)


def generate_oas(apps: List[Application]) -> dict:
    """
    Generate and return Open Api Specification from PydanticView in application.
    """
    oas = OpenApiSpec3()
    links_builder = LinksBuilder()
    for app in apps:
        for resources in app.router.resources():
            for resource_route in resources:
                if not is_pydantic_view(resource_route.handler):
                    continue

                view: Type[PydanticView] = resource_route.handler
                info = resource_route.get_info()
                path = oas.paths[info.get("path", info.get("formatter"))]
                if resource_route.method == "*":
                    for method_name in view.allowed_methods:
                        _add_http_method_to_oas(
                            oas, path, method_name, view, links_builder
                        )
                else:
                    _add_http_method_to_oas(
                        oas, path, resource_route.method, view, links_builder
                    )
    links_builder.build_links()
    return oas.spec


async def get_oas(request):
    """
    View to generate the Open Api Specification from PydanticView in application.
    """
    apps = request.app["apps to expose"]
    return json_response(generate_oas(apps))


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
