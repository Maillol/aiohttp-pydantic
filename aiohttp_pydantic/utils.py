from pydantic import BaseModel


def is_pydantic_base_model(obj):
    """
    Return true is obj is a pydantic.BaseModel subclass.
    """
    try:
        return issubclass(obj, BaseModel)
    except TypeError:
        return False
