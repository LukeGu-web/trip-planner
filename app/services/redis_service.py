from redis import asyncio as aioredis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisService:
    _instance = None
    _redis = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def get_redis(cls):
        """Get Redis connection instance"""
        if cls._redis is None:
            try:
                # Create Redis connection
                redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                cls._redis = await aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                cls._redis = None
                raise e
        return cls._redis

    @classmethod
    async def check_health(cls) -> dict:
        """Check Redis connection health"""
        try:
            redis = await cls.get_redis()
            if redis is None:
                return {"status": "unhealthy", "message": "Redis connection not established"}
            
            # Try to ping Redis
            await redis.ping()
            return {"status": "healthy", "message": "Connected to Redis"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Redis error: {str(e)}"} 