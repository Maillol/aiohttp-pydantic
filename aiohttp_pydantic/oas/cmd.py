import argparse
import importlib
import json

from .view import generate_oas


def application_type(value):
    """
    Return aiohttp application defined in the value.
    """
    try:
        module_name, app_name = value.split(":")
    except ValueError:
        module_name, app_name = value, "app"

    module = importlib.import_module(module_name)
    try:
        if app_name.endswith("()"):
            app_name = app_name.strip("()")
            factory_app = getattr(module, app_name)
            return factory_app()
        return getattr(module, app_name)

    except AttributeError as error:
        raise argparse.ArgumentTypeError(error) from error


def setup(parser: argparse.ArgumentParser):
    parser.add_argument(
        "apps",
        metavar="APP",
        type=application_type,
        nargs="*",
        help="The name of the module containing the asyncio.web.Application."
        " By default the variable named 'app' is loaded but you can define"
        " an other variable name ending the name of module with : characters"
        " and the name of variable. Example: my_package.my_module:my_app",
    )

    parser.set_defaults(func=show_oas)


def show_oas(args: argparse.Namespace):
    print(json.dumps(generate_oas(args.apps), sort_keys=True, indent=4))
