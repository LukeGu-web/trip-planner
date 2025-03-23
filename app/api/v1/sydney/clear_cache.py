from fastapi import APIRouter, HTTPException
from app.services.redis_service import RedisService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/clear-translation-cache", 
            summary="Clear Sydney Station Name Translation Cache",
            description="Clear all station name translation cache stored in Redis for Sydney")
async def clear_translation_cache():
    """
    Clear all station name translation cache stored in Redis for Sydney.
    This operation will delete all cache keys with prefix 'station_translation:'.
    """
    try:
        redis = await RedisService.get_redis()
        if not redis:
            raise HTTPException(status_code=503, detail="Redis service not connected")
            
        # Use pattern matching to delete all translation cache
        pattern = "station_translation:*"
        keys = await redis.keys(pattern)
        
        if not keys:
            return {"message": "No translation cache found to clear"}
            
        # Batch delete matching keys
        await redis.delete(*keys)
        
        logger.info(f"Successfully cleared {len(keys)} translation cache entries")
        return {
            "message": f"Successfully cleared {len(keys)} translation cache entries",
            "cleared_keys_count": len(keys)
        }
        
    except Exception as e:
        logger.error(f"Error occurred while clearing translation cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error occurred while clearing cache: {str(e)}") 