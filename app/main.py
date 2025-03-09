from fastapi import FastAPI
from redis import Redis
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI(
    title="FastAPI Redis App",
    description="An application built with FastAPI and Redis",
    version="1.0.0"
)

# Redis connection
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI + Redis Application"}

@app.get("/ping")
async def ping_redis():
    try:
        response = redis_client.ping()
        return {"status": "success", "message": "Redis connection successful!"}
    except Exception as e:
        return {"status": "error", "message": f"Redis connection failed: {str(e)}"} 