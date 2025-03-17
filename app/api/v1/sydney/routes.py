from fastapi import APIRouter

from . import trip, service_alerts

router = APIRouter(prefix="/sydney", tags=["Sydney"])

# Include trip planning routes
router.include_router(trip.router)

# Include service alerts routes
router.include_router(service_alerts.router, tags=["Sydney"]) 