import os
from cryptography.fernet import Fernet
import aioredis
import redis


class Settings:
    # todo define, load and store general station configuration
    def load_station_config_yaml(self):
        pass

    @staticmethod
    def get_fernet():
        # todo get key from config file
        key = os.getenv('FERNET_KEY').encode()
        if key is None:
            raise ValueError("No Fernet key provided")
        return Fernet(key)

    @staticmethod
    def get_sync_redis() -> redis.Redis:
        """
        Obtain a synchronous redis connection based on environment variables.

        Returns:

        """
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', 6379)
        return redis.Redis(host=redis_host, port=redis_port)

    @staticmethod
    def get_async_redis() -> aioredis.Redis:
        """
        Obtain an asynchronous redis connection based on environment variables

        Returns:

        """
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', 6379)
        redis_url = f"redis://{redis_host}:{redis_port}/0"
        return aioredis.from_url(redis_url)

    @property
    def cache_ttl(self) -> int:
        return int(os.getenv('CACHE_TTL', 300))

    @property
    def cache_key_prefix(self) -> str:
        return os.getenv("CACHE_KEY_PREFIX", "station-cache-")


class LogConfig:
    pass


settings = Settings()
