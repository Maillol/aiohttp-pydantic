from aiohttp.web import AppKey

from .model import Model
from .schema import User

MODEL = AppKey("model", Model)
CURRENT_USER = AppKey("current_user", User)
