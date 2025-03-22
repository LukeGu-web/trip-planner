import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_tfnsw_service
from app.services.tfnsw_service import TfnswService
from app.models.trip import TripRequest, TripResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/trip", response_model=TripResponse)
async def get_trip_plan(
    from_location: str,
    to_location: str,
    departure_time: Optional[str] = None,
    language_code: str = "en",
    tfnsw_service: TfnswService = Depends(get_tfnsw_service)
) -> Dict[str, Any]:
    """
    Get trip planning information between two locations
    
    Args:
        from_location: Starting location (stop name or ID)
        to_location: Destination location (stop name or ID)
        departure_time: Optional departure time in ISO format
        language_code: Language code for station name translations (default: "en")
        
    Returns:
        Trip planning information
    """
    try:
        logger.info(f"Received trip plan request: from {from_location} to {to_location}, time: {departure_time or 'now'}, language: {language_code}")
        
        # Validate request
        trip_request = TripRequest(
            from_location=from_location,
            to_location=to_location,
            departure_time=departure_time
        )
        trip_request.validate_request()
        logger.debug("Request validation successful")
        
        # Get trip plan
        response = await tfnsw_service.get_trip_plan(
            trip_request.from_location,
            trip_request.to_location,
            trip_request.departure_time
        )
        
        # Format response with translation
        formatted_response = await tfnsw_service.format_trip_response(response, language_code)
        logger.info(f"Found {len(formatted_response['journeys'])} possible journeys")
        
        return formatted_response
        
    except ValueError as e:
        logger.error(f"Request validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get trip plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get trip plan: {str(e)}") 