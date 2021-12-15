from typing import Union, Any

from pydantic import BaseModel
from station.app.config import Settings


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
