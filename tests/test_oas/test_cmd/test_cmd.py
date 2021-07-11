import argparse
from textwrap import dedent
from io import StringIO
from pathlib import Path
import pytest

from aiohttp_pydantic.oas import cmd

PATH_TO_BASE_JSON_FILE = str(Path(__file__).parent / "oas_base.json")


@pytest.fixture
def cmd_line():
    parser = argparse.ArgumentParser()
    cmd.setup(parser)
    return parser


def test_show_oas_of_app(cmd_line):
    args = cmd_line.parse_args(["tests.test_oas.test_cmd.sample"])
    args.output = StringIO()
    args.func(args)

    expected = dedent(
        """
    {
        "info": {
            "title": "Aiohttp pydantic application",
            "version": "1.0.0"
        },
        "openapi": "3.0.0",
        "paths": {
            "/route-1/{a}": {
                "get": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "a",
                            "required": true,
                            "schema": {
                                "title": "a",
                                "type": "integer"
                            }
                        }
                    ]
                }
            },
            "/sub-app/route-2/{b}": {
                "post": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "b",
                            "required": true,
                            "schema": {
                                "title": "b",
                                "type": "integer"
                            }
                        }
                    ]
                }
            }
        }
    }
    """
    )

    assert args.output.getvalue().strip() == expected.strip()


def test_show_oas_of_sub_app(cmd_line):
    args = cmd_line.parse_args(["tests.test_oas.test_cmd.sample:sub_app"])
    args.output = StringIO()
    args.func(args)
    expected = dedent(
        """
    {
        "info": {
            "title": "Aiohttp pydantic application",
            "version": "1.0.0"
        },
        "openapi": "3.0.0",
        "paths": {
            "/sub-app/route-2/{b}": {
                "post": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "b",
                            "required": true,
                            "schema": {
                                "title": "b",
                                "type": "integer"
                            }
                        }
                    ]
                }
            }
        }
    }
    """
    )

    assert args.output.getvalue().strip() == expected.strip()


def test_show_oas_of_a_callable(cmd_line):
    args = cmd_line.parse_args(
        [
            "tests.test_oas.test_cmd.sample:make_app()",
            "--base-oas-file",
            PATH_TO_BASE_JSON_FILE,
        ]
    )
    args.output = StringIO()
    args.func(args)
    expected = dedent(
        """
        {
        "info": {
            "title": "Aiohttp pydantic application",
            "version": "1.0.0"
        },
        "openapi": "3.0.0",
        "paths": {
            "/route-3/{a}": {
                "get": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "a",
                            "required": true,
                            "schema": {
                                "title": "a",
                                "type": "integer"
                            }
                        }
                    ]
                }
            }
        }
    }
    """
    )

    assert args.output.getvalue().strip() == expected.strip()
