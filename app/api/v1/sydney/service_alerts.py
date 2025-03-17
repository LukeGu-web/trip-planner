from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional, List
from app.services.tfnsw_service import TfnswService
from app.core.deps import get_tfnsw_service
import httpx
import logging
from datetime import datetime
import pytz

router = APIRouter()
logger = logging.getLogger(__name__)

# Set Sydney timezone
SYDNEY_TIMEZONE = pytz.timezone('Australia/Sydney')

async def get_stop_id(tfnsw_service: TfnswService, location: str) -> Optional[str]:
    """
    Get stop ID from stop name
    
    Args:
        tfnsw_service: TFNSW service instance
        location: Stop name
        
    Returns:
        Stop ID or None
    """
    try:
        params = {
            "outputFormat": "rapidJSON",
            "type_sf": "any",
            "name_sf": location,
            "version": "10.2.1.42"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{tfnsw_service.base_url}/stop_finder",
                headers=tfnsw_service.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Find first stop result
            if "locations" in data and data["locations"]:
                for location in data["locations"]:
                    if location.get("type") == "stop":
                        return location.get("id")
            
            logger.warning(f"Stop ID not found: {location}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get stop ID: {str(e)}")
        return None

@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_service_alerts(
    from_location: str,
    to_location: str,
    tfnsw_service: TfnswService = Depends(get_tfnsw_service)
) -> List[Dict[str, Any]]:
    """
    Get service alerts between two stops for today
    
    Args:
        from_location: Starting stop name or ID
        to_location: Destination stop name or ID
        
    Returns:
        List of service alerts
    """
    try:
        # Get stop IDs
        from_stop_id = await get_stop_id(tfnsw_service, from_location)
        to_stop_id = await get_stop_id(tfnsw_service, to_location)
        
        if not from_stop_id or not to_stop_id:
            raise HTTPException(
                status_code=400,
                detail="Could not find specified stops. Please check stop names."
            )
        
        # Get today's date in Sydney timezone
        today = datetime.now(SYDNEY_TIMEZONE)
        date_str = today.strftime("%d-%m-%Y")
        
        # Build request parameters
        params = {
            "outputFormat": "rapidJSON",
            "coordOutputFormat": "EPSG:4326",
            "filterDateValid": date_str,
            "filterPublicationStatus": "current",
            "itdLPxx_selStop": f"{from_stop_id},{to_stop_id}",
            "version": "10.2.1.42"
        }
        
        # Call TFNSW API to get service alerts
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{tfnsw_service.base_url}/add_info",
                headers=tfnsw_service.headers,
                params=params
            )
            
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Authentication failed. Please check API key")
            elif response.status_code == 403:
                raise HTTPException(status_code=403, detail="Access forbidden. API key may not have required permissions")
            
            # Return empty list if no alerts found
            if response.status_code == 404:
                logger.info(f"No service alerts found between {from_location} and {to_location}")
                return []
            
            response.raise_for_status()
            response_data = response.json()
            
            # Format response data - only return current alerts
            alerts = response_data.get("infos", {}).get("current", [])
            
            # Simplify alert data
            simplified_alerts = []
            for alert in alerts:
                simplified_alert = {
                    "id": alert.get("id"),
                    "priority": alert.get("priority"),
                    "title": alert.get("subtitle"),
                    "content": alert.get("content"),
                    "affected_stops": [
                        {
                            "id": stop.get("id"),
                            "name": stop.get("name")
                        }
                        for stop in alert.get("affected", {}).get("stops", [])
                    ],
                    "affected_lines": [
                        {
                            "id": line.get("id"),
                            "name": line.get("name"),
                            "number": line.get("number")
                        }
                        for line in alert.get("affected", {}).get("lines", [])
                    ]
                }
                simplified_alerts.append(simplified_alert)
            
            return simplified_alerts
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"HTTP request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get service alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get service alerts: {str(e)}") 