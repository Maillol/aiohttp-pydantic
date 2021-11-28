from uuid import UUID

from pydantic import BaseModel

from aiohttp_pydantic.injectors import FuncSignatureParser


class User(BaseModel):
    firstname: str
    lastname: str


def test_parse_func_signature():

    def body_only(self, user: User):
        pass

    def path_only(self, id: str, /):
        pass

    def qs_only(self, page: int):
        pass

    def header_only(self, *, auth: UUID):
        pass

    def path_and_qs(self, id: str, /, page: int):
        pass

    def path_and_header(self, id: str, /, *, auth: UUID):
        pass

    def qs_and_header(self, page: int, *, auth: UUID):
        pass

    def path_qs_and_header(self, id: str, /, page: int, *, auth: UUID):
        pass

    def path_body_qs_and_header(self, id: str, /, user: User, page: int, *, auth: UUID):
        pass

    assert FuncSignatureParser().parse(body_only) == ({}, {"user": User}, {}, {}, {})
    assert FuncSignatureParser().parse(path_only) == ({"id": str}, {}, {}, {}, {})
    assert FuncSignatureParser().parse(qs_only) == ({}, {}, {"page": int}, {}, {})
    assert FuncSignatureParser().parse(header_only) == ({}, {}, {}, {"auth": UUID}, {})
    assert FuncSignatureParser().parse(path_and_qs) == (
        {"id": str},
        {},
        {"page": int},
        {},
        {},
    )
    assert FuncSignatureParser().parse(path_and_header) == (
        {"id": str},
        {},
        {},
        {"auth": UUID},
        {},
    )
    assert FuncSignatureParser().parse(qs_and_header) == (
        {},
        {},
        {"page": int},
        {"auth": UUID},
        {},
    )
    assert FuncSignatureParser().parse(path_qs_and_header) == (
        {"id": str},
        {},
        {"page": int},
        {"auth": UUID},
        {},
    )
    assert FuncSignatureParser().parse(path_body_qs_and_header) == (
        {"id": str},
        {"user": User},
        {"page": int},
        {"auth": UUID},
        {},
    )
