from fastapi import APIRouter, HTTPException
from app.services.tfnsw_service import TfnswService
from app.schemas.trip import TripRequest, TripResponse
from datetime import datetime
import logging

router = APIRouter(prefix="/sydney", tags=["sydney"])
tfnsw_service = TfnswService()
logger = logging.getLogger(__name__)

@router.get("/trip", response_model=TripResponse)
async def get_trip_plan(
    from_location: str,
    to_location: str,
    departure_time: str = None
):
    """
    Get trip planning information between two locations in Sydney using Transport for NSW API
    
    Args:
        from_location: Starting location (stop name or ID)
        to_location: Destination location (stop name or ID)
        departure_time: Optional reference time in ISO format (e.g., 2024-03-09T08:30:00)
        
    Returns:
        List of possible journeys with timing and route information
    """
    logger.info(f"Received Sydney trip plan request: from={from_location} to={to_location} "
                f"departure_time={departure_time}")
    
    try:
        # Validate request using Pydantic model
        request = TripRequest(
            from_location=from_location,
            to_location=to_location,
            departure_time=departure_time
        )
        request.validate_request()
        logger.debug("Request validation successful")
        
        # Get response from Transport for NSW API
        response = await tfnsw_service.get_trip_plan(
            from_location=request.from_location,
            to_location=request.to_location,
            departure_time=request.departure_time
        )
        
        # Format the response
        formatted_response = tfnsw_service.format_trip_response(response)
        logger.info(f"Found {len(formatted_response['journeys'])} possible journeys")
        
        return formatted_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 