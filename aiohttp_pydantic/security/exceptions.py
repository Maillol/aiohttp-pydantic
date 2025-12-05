"""
Security-related exceptions for authentication and authorization.
"""


class SecurityException(Exception):
    """
    Base exception for all security-related errors.

    All authentication and authorization exceptions inherit from this class,
    allowing for easy catching of any security error.
    """


class AuthenticationError(SecurityException):
    """
    Raised when user authentication fails.

    This indicates the user could not be identified (missing credentials,
    invalid token, expired session, etc.). Should typically result in a
    401 Unauthorized HTTP response.
    """


class AuthorizationError(SecurityException):
    """
    Raised when an authenticated user lacks required permissions.

    This indicates the user was successfully authenticated but does not
    have permission to perform the requested operation. Should typically
    result in a 403 Forbidden HTTP response.
    """
