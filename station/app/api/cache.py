from typing import Union, Any
from pydantic import BaseModel
from station.app.config import Settings
from functools import wraps


def cache(route):
    """
    Decorator to cache a route.
    """

    @wraps(route)
    async def wrapper(*args, **kwargs):
        key = str(Settings.cache_key_prefix) + route.__name__
        response = cache_get_sync(key)
        if response is None:
            response = await route(*args, **kwargs)
            cache_set_sync(key, response)
        return response

    return wrapper


def cache_set_sync(key: str, response: BaseModel, ttl: int = None) -> None:
    """
    Set a value in the redis for caching.
    """
    redis = Settings.get_sync_redis()
    if ttl is None:
        ttl = Settings.cache_ttl
    redis.set(key, response.json(), ex=ttl)


def cache_get_sync(key: str) -> Union[Union[str, bytes, None], Any]:
    """
    Get a value from the redis cache.
    """
    redis = Settings.get_sync_redis()
    if redis.exists(key):
        return redis.get(key)
    else:
        return None
