"""
Security module for aiohttp-pydantic.

Provides authentication and authorization primitives for aiohttp applications.
"""

from typing import Any

from aiohttp.web import Application

from aiohttp_pydantic.security._types import IdT, RuleT
from aiohttp_pydantic.security.base import AUTH_SCHEMES, AuthSchemeRef, SecurityScheme
from aiohttp_pydantic.security.middleware import security_middleware


def _cleanup_ctx_factory(security_scheme: SecurityScheme[Any, Any]):
    """
    Create a cleanup context for a security scheme.

    Ensures startup() is called when the app starts and cleanup()
    is called when the app shuts down.
    """

    async def cleanup_ctx(app: Application):
        await security_scheme.startup(app)
        yield
        await security_scheme.cleanup(app)

    return cleanup_ctx


def setup(
    app: Application,
    schemes: dict[AuthSchemeRef[RuleT, IdT], SecurityScheme[IdT, RuleT]],
) -> None:
    """
    Configure security schemes for the application.

    This must be called once during application setup, before starting the server.
    Registers all security schemes and sets up their lifecycle (startup/cleanup).

    Args:
        app: The aiohttp Application instance
        schemes: Dict mapping AuthSchemeRef to SecurityScheme instances

    Raises:
        RuntimeError: If setup() has already been called on this application

    Example:
        >>> USER_AUTH = SecurityScheme.ref("user_auth")
        >>> app = web.Application()
        >>> setup(app, {USER_AUTH: MySecurityScheme()})
    """
    if AUTH_SCHEMES in app:
        raise RuntimeError(
            "Security schemes already configured. Call setup() only once."
        )

    app[AUTH_SCHEMES] = schemes

    for scheme in schemes.values():  # ← pas besoin de _, scheme
        app.cleanup_ctx.append(_cleanup_ctx_factory(scheme))

    app.middlewares.append(security_middleware)
