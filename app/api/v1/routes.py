from fastapi import APIRouter
from app.api.v1.sydney import routes as sydney_routes

router = APIRouter()

# Include city-specific routes
router.include_router(sydney_routes.router) 