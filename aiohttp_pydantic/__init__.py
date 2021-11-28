from .view import PydanticView


unpack_request = PydanticView.decorator()

__version__ = "1.12.0"

__all__ = ("PydanticView", "unpack_request", "__version__")
