import json
import logging
from typing import Dict, Any
import httpx
from datetime import datetime
from app.utils.date_utils import SYDNEY_TIMEZONE

# Configure logging
logger = logging.getLogger(__name__)

async def make_api_request(base_url: str, endpoint: str, headers: Dict[str, str], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send request to external API and handle response
    
    Args:
        base_url: Base URL of the API
        endpoint: API endpoint
        headers: Request headers
        params: Request parameters
        
    Returns:
        JSON data from API response
    """
    # Build complete request URL for logging
    full_url = f"{base_url}/{endpoint}?{httpx.QueryParams(params)}"
    logger.debug(f"Sending request to API: GET@{full_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/{endpoint}",
                headers=headers,
                params=params
            )
            
            if response.status_code == 401:
                logger.error("Authentication failed. Please check your API key")
                raise Exception("Authentication failed. Please check your API key")
            elif response.status_code == 403:
                logger.error("Access forbidden. Your API key may not have required permissions")
                raise Exception("Access forbidden. Your API key may not have required permissions")
            elif response.status_code == 404:
                logger.error("Resource not found. Please check the requested URL and parameters")
                raise Exception("Resource not found. Please check the requested URL and parameters")
            
            response.raise_for_status()
            
            response_data = response.json()
            logger.debug(f"API response status code: {response.status_code}")
            
            return response_data
                
    except httpx.HTTPError as e:
        error_msg = f"HTTP request failed: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f"\nResponse status code: {e.response.status_code}"
            try:
                error_details = e.response.json()
                error_msg += f"\nError details: {json.dumps(error_details)}"
            except:
                error_msg += f"\nResponse text: {e.response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise Exception(f"Request failed: {str(e)}")

def filter_journeys_by_time(journeys: list, reference_time: str = None) -> list:
    """
    Filter journeys based on reference time
    
    Args:
        journeys: List of journeys
        reference_time: Reference time in ISO format
        
    Returns:
        Filtered list of journeys
    """
    if not journeys:
        return []
        
    reference_dt = None
    if reference_time:
        # Parse the input time string
        reference_dt = datetime.fromisoformat(reference_time)
        # If the datetime is naive (no timezone info), assume it's Sydney time
        if reference_dt.tzinfo is None:
            reference_dt = SYDNEY_TIMEZONE.localize(reference_dt)
    else:
        reference_dt = datetime.now(SYDNEY_TIMEZONE)
    
    filtered_journeys = []
    for journey in journeys:
        if journey.get("legs"):
            first_leg = journey["legs"][0]
            departure_time = first_leg.get("origin", {}).get("departureTimePlanned")
            if departure_time:
                journey_dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                journey_dt = journey_dt.astimezone(SYDNEY_TIMEZONE)
                if journey_dt >= reference_dt:
                    filtered_journeys.append(journey)
    
    logger.debug(f"Number of journeys after filtering: {len(filtered_journeys)}")
    return filtered_journeys 