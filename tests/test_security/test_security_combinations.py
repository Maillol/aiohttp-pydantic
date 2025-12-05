from aiohttp_pydantic.security.auth_scheme import APIKeySecurityScheme
from aiohttp_pydantic.security import setup
from aiohttp import web
from aiohttp.test_utils import make_mocked_request
import pytest


class APIKeyAuth(APIKeySecurityScheme):

    async def authenticate(self, request: web.Request) -> str:
        return self.extract_credentials(request)

    async def permits(self, request, identity: str, rule: str, context: dict) -> bool:
        return True

    def to_openapi_scopes(self, rule: str) -> list[str]:
        return [rule]


class APIKeyAuthA(APIKeyAuth):
    parameter_name = "X-Api-Key-A"


class APIKeyAuthB(APIKeyAuth):
    parameter_name = "X-Api-Key-B"


class APIKeyAuthC(APIKeyAuth):
    parameter_name = "X-Api-Key-C"


class APIKeyAuthD(APIKeyAuth):
    parameter_name = "X-Api-Key-D"


A = APIKeyAuthA.ref("A")
B = APIKeyAuthB.ref("B")
C = APIKeyAuthC.ref("C")
D = APIKeyAuthD.ref("D")



@pytest.fixture
def app_with_auth():
    app = web.Application()
    setup(app, {
        A: APIKeyAuthA(),
        B: APIKeyAuthB(),
        C: APIKeyAuthC(),
        D: APIKeyAuthD()
    })
    return app

def test_oas_with_operator_or(app_with_auth):

    assert (A.rule("r") | B.rule("read")).to_openapi_security(app_with_auth) == [
        {
            "A": ["r"],
        },
        {
            "B": ["read"],
        },
    ]

    assert (A.rule("r") | B.rule("r") | C.rule("r")).to_openapi_security(app_with_auth) == [
        {
            "A": ["r"],
        },
        {
            "B": ["r"],
        },
        {
            "C": ["r"],
        },
    ]
    assert (
        A.rule("r") | B.rule("r+") | C.rule("r++") | D.rule("r+++")
    ).to_openapi_security(app_with_auth) == [
        {
            "A": ["r"],
        },
        {
            "B": ["r+"],
        },
        {
            "C": ["r++"],
        },
        {
            "D": ["r+++"],
        },
    ]


def test_oas_with_operator_and(app_with_auth):


    assert (A.rule("r") & B.rule("r")).to_openapi_security(app_with_auth) == [
        {"A": ["r"], "B": ["r"]}
    ]

    assert (A.rule("r") & B.rule("r") & C.rule("r")).to_openapi_security(app_with_auth) == [
        {"A": ["r"], "B": ["r"], "C": ["r"]}
    ]

    assert (A.rule("r") & B.rule("r") & C.rule("r") & D.rule("r")).to_openapi_security(
        app_with_auth
    ) == [{"A": ["r"], "B": ["r"], "C": ["r"], "D": ["r"]}]


def test_oas_or_of_and_groups(app_with_auth):

    assert (
        (A.rule("r") & B.rule("r")) | (C.rule("r") & D.rule("r"))
    ).to_openapi_security(app_with_auth) == [{"A": ["r"], "B": ["r"]}, {"C": ["r"], "D": ["r"]}]


def test_oas_and_of_or_groups(app_with_auth):

    assert (
        (A.rule("r") | B.rule("r+")) & (C.rule("r++") | D.rule("r+++"))
    ).to_openapi_security(app_with_auth) == [
        {"A": ["r"], "C": ["r++"]},
        {"A": ["r"], "D": ["r+++"]},
        {"B": ["r+"], "C": ["r++"]},
        {"B": ["r+"], "D": ["r+++"]},
    ]


async def test_authn_authz_with_operator_or(app_with_auth):

    rule_a = A.rule("r")
    rule_b = B.rule("read")
    rule_c = C.rule("r")
    rule_d = D.rule("read")

    combined_rule = rule_a | rule_b | rule_c | rule_d

    request = make_mocked_request("GET", "/", app=app_with_auth, headers={"X-Api-Key-C": "x"})
    identities = await combined_rule.authn(request)
    assert len(identities) == 1
    rule, identity = identities[0]
    assert rule is rule_c
    await rule.authz(request, identity, {})


async def test_authn_authz_with_operator_and(app_with_auth):

    rule_a = A.rule("r")
    rule_b = B.rule("read")
    rule_c = C.rule("r")
    rule_d = D.rule("read")

    combined_rule = rule_a & rule_b & rule_c & rule_d

    request = make_mocked_request("GET", "/", app=app_with_auth, headers={"X-Api-Key-A": "x"})
    try:
        await combined_rule.authn(request)
    except ExceptionGroup as error:
        assert len(error.exceptions) == 1
        assert str(error.exceptions[0]) == "X-Api-Key-B missing in header"
    else:
        raise AssertionError("ExceptionGroup is not raised")


async def test_authn_authz_or_of_and_groups(app_with_auth):

    rule_a = A.rule("r")
    rule_b = B.rule("read")
    rule_c = C.rule("r")
    rule_d = D.rule("read")

    combined_rule = (rule_a | rule_b) & (rule_c | rule_d)

    request = make_mocked_request("GET", "/", app=app_with_auth, headers={"X-Api-Key-C": "x"})
    try:
        await combined_rule.authn(request)
    except ExceptionGroup as error:
        assert len(error.exceptions) == 2
        assert [str(exc) for exc in error.exceptions] == [
            "X-Api-Key-A missing in header",
            "X-Api-Key-B missing in header",
        ]
    else:
        raise AssertionError("ExceptionGroup is not raised")

    request = make_mocked_request(
        "GET", "/", app=app_with_auth, headers={"X-Api-Key-C": "ccc", "X-Api-Key-A": "aaa"}
    )
    identities = await combined_rule.authn(request)
    assert len(identities) == 2
    rule, identity = identities[0]
    assert rule is rule_a
    assert identity == "aaa"
    await rule.authz(request, identity, {})

    rule, identity = identities[1]
    assert rule is rule_c
    assert identity == "ccc"
    await rule.authz(request, identity, {})


async def test_authn_authz_and_of_or_groups(app_with_auth):
    rule_a = A.rule("r")
    rule_b = B.rule("read")
    rule_c = C.rule("r")
    rule_d = D.rule("read")

    combined_rule = (rule_a & rule_b) | (rule_c & rule_d)

    request = make_mocked_request("GET", "/", app=app_with_auth, headers={"X-Api-Key-C": "x"})
    try:
        await combined_rule.authn(request)
    except ExceptionGroup as error:
        assert len(error.exceptions) == 2
        assert [str(exc) for exc in error.exceptions] == [
            "X-Api-Key-A missing in header",
            "X-Api-Key-D missing in header",
        ]
    else:
        raise AssertionError("ExceptionGroup is not raised")

    request = make_mocked_request(
        "GET", "/", app=app_with_auth, headers={"X-Api-Key-C": "ccc", "X-Api-Key-D": "ddd"}
    )
    identities = await combined_rule.authn(request)
    assert len(identities) == 2
    rule, identity = identities[0]
    assert rule is rule_c
    assert identity == "ccc"
    await rule.authz(request, identity, {})

    rule, identity = identities[1]
    assert rule is rule_d
    assert identity == "ddd"
    await rule.authz(request, identity, {})
