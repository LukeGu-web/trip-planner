from fastapi import APIRouter
from app.api.v1.sydney import routes as sydney_routes
from app.services.redis_service import RedisService
from typing import Dict

router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify API and Redis status
    
    Returns:
        Dict containing health status of the service and Redis
    """
    # Check Redis health
    redis_health = await RedisService.check_health()
    
    # Overall status is healthy only if Redis is also healthy
    status = "healthy" if redis_health["status"] == "healthy" else "unhealthy"
    
    return {
        "status": status,
        "redis": redis_health["message"]
    }

# Include city-specific routes
router.include_router(sydney_routes.router) 