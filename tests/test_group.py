from __future__ import annotations

import pytest

from aiohttp_pydantic.injectors import (
    Group,
    _get_group_signature,
    _unpack_group_in_signature,
    DuplicateNames,
)


def test_get_group_signature_with_a2b2():
    class A(Group):
        a: int = 1

    class B(Group):
        b: str = "b"

    class B2(B):
        b: str = "b2"  # Overwrite default value

    class A2(A):
        a: int  # Remove default value

    class A2B2(A2, B2):
        ab2: float

    assert ({"ab2": float, "a": int, "b": str}, {"b": "b2"}) == _get_group_signature(
        A2B2
    )


def test_unpack_group_in_signature():
    class PaginationGroup(Group):
        page: int
        page_size: int = 20

    args = {"pagination": PaginationGroup, "name": str, "age": int}

    default = {"age": 18}

    _unpack_group_in_signature(args, default)

    assert args == {"page": int, "page_size": int, "name": str, "age": int}

    assert default == {"age": 18, "page_size": 20}


def test_unpack_group_in_signature_with_duplicate_error():
    class PaginationGroup(Group):
        page: int
        page_size: int = 20

    args = {"pagination": PaginationGroup, "page": int, "age": int}

    with pytest.raises(DuplicateNames) as e_info:
        _unpack_group_in_signature(args, {})

    assert e_info.value.group is PaginationGroup
    assert e_info.value.attr_name == "page"


def test_unpack_group_in_signature_with_parameters_overwrite():
    class PaginationGroup(Group):
        page: int = 0
        page_size: int = 20

    args = {"page": PaginationGroup, "age": int}

    default = {}
    _unpack_group_in_signature(args, default)

    assert args == {"page": int, "page_size": int, "age": int}

    assert default == {"page": 0, "page_size": 20}
