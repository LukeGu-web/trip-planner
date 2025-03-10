from fastapi import FastAPI
from redis.asyncio import Redis
from dotenv import load_dotenv
from app.core.config import settings
from app.api.v1.routes import router as api_router

# Load environment variables
load_dotenv()

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend for Frontend service for Transport for NSW Trip Planner API",
    version=settings.APP_VERSION
)

# Redis connection
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    try:
        redis_response = await redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected" if redis_response else "disconnected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis": f"error: {str(e)}"
        } 