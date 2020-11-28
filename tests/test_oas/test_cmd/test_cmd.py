import argparse
from textwrap import dedent

import pytest

from aiohttp_pydantic.oas import cmd


@pytest.fixture
def cmd_line():
    parser = argparse.ArgumentParser()
    cmd.setup(parser)
    return parser


def test_show_oad_of_app(cmd_line, capfd):
    args = cmd_line.parse_args(["tests.test_oas.test_cmd.sample"])
    args.func(args)
    captured = capfd.readouterr()
    expected = dedent(
        """
        {
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

    assert captured.out.strip() == expected.strip()


def test_show_oad_of_sub_app(cmd_line, capfd):
    args = cmd_line.parse_args(["tests.test_oas.test_cmd.sample:sub_app"])
    args.func(args)
    captured = capfd.readouterr()
    expected = dedent(
        """
        {
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

    assert captured.out.strip() == expected.strip()


def test_show_oad_of_a_callable(cmd_line, capfd):
    args = cmd_line.parse_args(["tests.test_oas.test_cmd.sample:make_app()"])
    args.func(args)
    captured = capfd.readouterr()
    expected = dedent(
        """
        {
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

    assert captured.out.strip() == expected.strip()
