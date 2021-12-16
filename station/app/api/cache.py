from typing import Union, Any, List
from pydantic import BaseModel
from station.app.config import Settings
from functools import wraps
import json


def cache(route):
    """
    Decorator to cache a route and access the cache if it is available.
    """
    print("Caching route: {}".format(route))

    @wraps(route)
    async def wrapper(*args, **kwargs):
        key = str(Settings.cache_key_prefix) + route.__name__
        response = cache_get_sync(key)
        if response is None:
            response = route(*args, **kwargs)
            cache_set_sync(key, response)
        return response

    return wrapper


def cache_set_sync(key: str, response: Union[BaseModel, List[BaseModel]], ttl: int = None) -> None:
    """
    Set a value in the redis for caching.
    """
    redis = Settings.get_sync_redis()
    if ttl is None:
        ttl = Settings.cache_ttl

    # serialize the list of responses to json
    if isinstance(response, list):
        print(response)
        response_dicts = [r.dict() for r in response]
        response_json = json.dumps(response_dicts)
        redis.set(key, response_json, ex=ttl)
    else:
        redis.set(key, response.json(), ex=ttl)


def cache_get_sync(key: str) -> Union[Union[str, bytes, None], Any]:
    """
    Get a value from the redis cache.
    """
    redis = Settings.get_sync_redis()
    if redis.exists(key):
        print("Cache hit for {}".format(key))
        return redis.get(key)
    else:
        return None
