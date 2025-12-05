from aiohttp import web

from aiohttp_pydantic.security.exceptions import AuthenticationError, AuthorizationError


@web.middleware
async def security_middleware(request, handler):
    """Handle authentication and authorization errors."""
    try:
        return await handler(request)
    except ExceptionGroup as error_group:
        auth_errors = [
            error
            for error in error_group.exceptions
            if isinstance(error, AuthenticationError)
        ]

        if auth_errors:
            return web.json_response(
                {
                    "error": "Authentication required",
                    "details": [str(e) for e in auth_errors],
                },
                status=401,
            )

        raise

    except AuthorizationError as error:
        return web.json_response(
            {"error": "Permission denied", "detail": str(error)}, status=403
        )
