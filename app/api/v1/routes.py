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
        
        # Get raw response from Transport for NSW API
        response = await tfnsw_service.get_trip_plan(
            from_location=request.from_location,
            to_location=request.to_location,
            departure_time=request.departure_time,
            arrival_time=request.arrival_time
        )
        
        # Format the response
        formatted_response = tfnsw_service.format_trip_response(response)
        
        return TripResponse(**formatted_response)
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trip plan: {str(e)}"
        ) 