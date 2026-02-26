from aiohttp.web import Application, json_response, middleware

from aiohttp_pydantic import oas, security

from .keys import MODEL
from .model import Conflict, Model, NotFound
from .security import USER_AUTH, JWTAuth
from .view import PetCollectionView, PetItemView, UserCollectionView, UserLoginView

JWT_SECRET = "a-string-secret-at-least-256-bits-long"


@middleware
async def not_found_to_404(request, handler):
    """
    Convert NotFound exceptions into HTTP 404 responses.

    This allows raising `NotFound(resource_id)` in the domain logic
    without having to manually handle HTTP responses.
    """
    try:
        return await handler(request)
    except NotFound as key:
        return json_response({"error": f"Resource {key} does not exist"}, status=404)


@middleware
async def conflict_to_409(request, handler):
    """
    Convert Conflict exceptions into HTTP 409 responses.

    Used for example when attempting to create a user
    with a username that already exists.
    """
    try:
        return await handler(request)
    except Conflict as error:
        return json_response({"error": str(error)}, status=409)


# Create the application with custom middlewares
# Note: The security middleware (401/403) will be automatically added by security.setup()
app = Application(middlewares=[not_found_to_404, conflict_to_409])

# Configure OpenAPI documentation (Swagger)
oas.setup(
    app,
    version_spec="1.0.1",
    title_spec="My Petstore",
)

# Configure authentication
# The security middleware will automatically be inserted first
# to handle AuthenticationError (401) and AuthorizationError (403)
security.setup(app, schemes={USER_AUTH: JWTAuth(jwt_secret=JWT_SECRET)})

# Initialize the "model" (in-memory database for the demo)
app[MODEL] = Model()

# Register routes
app.router.add_view("/pets", PetCollectionView)
app.router.add_view("/pets/{id}", PetItemView)
app.router.add_view("/users", UserCollectionView)
app.router.add_view("/users/login", UserLoginView)
