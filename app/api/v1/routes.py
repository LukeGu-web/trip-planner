from fastapi import APIRouter, HTTPException
from app.services.tfnsw_service import TfnswService
from app.schemas.trip import TripRequest, TripResponse
from datetime import datetime

router = APIRouter()
tfnsw_service = TfnswService()

@router.get("/trip", response_model=TripResponse)
async def get_trip_plan(
    from_location: str,
    to_location: str,
    departure_time: str = None,
    arrival_time: str = None
):
    """
    Get trip planning information between two locations
    
    Args:
        from_location: Starting location (stop name or ID)
        to_location: Destination location (stop name or ID)
        departure_time: Optional departure time in ISO format (e.g., 2024-03-09T08:30:00)
        arrival_time: Optional arrival time in ISO format (e.g., 2024-03-09T08:30:00)
        
    Returns:
        List of possible journeys with timing and route information
    """
    try:
        # Validate request using Pydantic model
        request = TripRequest(
            from_location=from_location,
            to_location=to_location,
            departure_time=departure_time,
            arrival_time=arrival_time
        )
        request.validate_times()
        
        # Get response from Transport for NSW API
        response = await tfnsw_service.get_trip_plan(
            from_location=request.from_location,
            to_location=request.to_location,
            departure_time=request.departure_time,
            arrival_time=request.arrival_time
        )
        
        # Format the response
        return tfnsw_service.format_trip_response(response)
    
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