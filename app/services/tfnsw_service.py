import httpx
from app.core.config import settings
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from urllib.parse import urlencode
import json
import pytz

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Set Sydney timezone
SYDNEY_TIMEZONE = pytz.timezone('Australia/Sydney')

class TfnswService:
    def __init__(self):
        self.base_url = settings.TFNSW_API_BASE_URL
        api_key = settings.TFNSW_API_KEY
        if not api_key:
            logger.error("TFNSW_API_KEY is not set in environment variables")
            raise ValueError("TFNSW_API_KEY is required")
            
        self.headers = {
            "Authorization": f"apikey {api_key}",
            "Accept": "application/json"
        }
        logger.debug(f"Initialized TfnswService with base URL: {self.base_url}")
    
    def _format_time(self, time_str: Optional[str]) -> tuple[str, str]:
        """Format time string into date and time components"""
        if not time_str:
            now = SYDNEY_TIMEZONE.localize(datetime.now())
            return now.strftime("%Y%m%d"), now.strftime("%H%M")
        
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # Convert to Sydney time
            sydney_dt = dt.astimezone(SYDNEY_TIMEZONE)
            return sydney_dt.strftime("%Y%m%d"), sydney_dt.strftime("%H%M")
        except ValueError as e:
            raise ValueError(f"Invalid time format. Expected ISO format (e.g., 2024-01-20T09:00:00): {e}")

    def _convert_to_sydney_time(self, time_str: str) -> str:
        """Convert UTC time string to Sydney time"""
        if not time_str or time_str == "Unknown":
            return time_str
        
        try:
            # Parse time string (assuming UTC input)
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # Convert to Sydney time
            sydney_time = dt.astimezone(SYDNEY_TIMEZONE)
            # Return formatted time string
            return sydney_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        except (ValueError, TypeError):
            return time_str
    
    async def get_trip_plan(self, 
                          from_location: str,
                          to_location: str,
                          departure_time: str = None) -> Dict[str, Any]:
        """
        Get trip planning information from Transport for NSW API
        
        Args:
            from_location: Starting location (can be stop ID or coordinates)
            to_location: Destination location (can be stop ID or coordinates)
            departure_time: Optional reference time in ISO format
            
        Returns:
            Dict containing the trip planning response
        """
        # Use provided time or current time as reference
        date_str, time_str = self._format_time(departure_time)
        
        params = {
            "outputFormat": "rapidJSON",
            "coordOutputFormat": "EPSG:4326",
            "itdDate": date_str,
            "itdTime": time_str,
            "depArrMacro": "dep",  # Always search for departures after the reference time
            "type_origin": "stop",
            "name_origin": from_location,
            "type_destination": "stop",
            "name_destination": to_location,
            "calcNumberOfTrips": "10",  # Fixed number of trips to return
            "wheelchair": "false",
            "TfNSWSF": "true",
            "version": "10.2.1.42"
        }
        
        # Build complete request URL for logging
        full_url = f"{self.base_url}/trip?{urlencode(params)}"
        logger.info(f"Making request to Transport for NSW API:")
        logger.info(f"GET@{full_url}")
        logger.debug(f"Request headers: {json.dumps({k: v if k != 'Authorization' else '[REDACTED]' for k, v in self.headers.items()})}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/trip",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 401:
                    logger.error("Authentication failed. Please check your API key")
                    raise Exception("Authentication failed. Please check your API key")
                elif response.status_code == 403:
                    logger.error("Access forbidden. Your API key may not have the required permissions")
                    raise Exception("Access forbidden. Your API key may not have the required permissions")
                
                response.raise_for_status()
                
                response_data = response.json()
                logger.info(f"Response status: {response.status_code}")
                
                # Log detailed response information
                journey_count = len(response_data.get("journeys", []))
                logger.info(f"Received {journey_count} journeys")
                
                # Filter out journeys before reference time
                if "journeys" in response_data:
                    reference_dt = None
                    if departure_time:
                        reference_dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                    else:
                        reference_dt = datetime.now(SYDNEY_TIMEZONE)
                    
                    filtered_journeys = []
                    for journey in response_data["journeys"]:
                        if journey.get("legs"):
                            first_leg = journey["legs"][0]
                            departure_time = first_leg.get("origin", {}).get("departureTimePlanned")
                            if departure_time:
                                journey_dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                                if journey_dt >= reference_dt:
                                    filtered_journeys.append(journey)
                    
                    response_data["journeys"] = filtered_journeys
                    logger.info(f"Filtered to {len(filtered_journeys)} journeys after reference time")
                
                if len(response_data.get("journeys", [])) == 0:
                    logger.warning("No journeys found. This might be due to:")
                    logger.warning("1. No available services for the requested time period")
                    logger.warning("2. Distance or complexity of the requested route")
                    
                    # Log the time span of returned journeys
                    if journey_count > 0:
                        journeys = response_data.get("journeys", [])
                        first_journey = journeys[0]
                        last_journey = journeys[-1]
                        
                        if first_journey.get("legs") and last_journey.get("legs"):
                            first_time = first_journey["legs"][0]["origin"].get("departureTimePlanned", "unknown")
                            last_time = last_journey["legs"][-1]["destination"].get("arrivalTimePlanned", "unknown")
                            logger.info(f"Journey time span: from {first_time} to {last_time}")
                
                # Log system messages if any
                if "systemMessages" in response_data:
                    logger.info("System messages from API:")
                    messages = response_data.get("systemMessages", {})
                    if isinstance(messages, dict):
                        for msg in messages.get("responseMessages", []):
                            if isinstance(msg, dict):
                                logger.info(f"- {msg.get('type', 'Unknown')}: {msg.get('error', 'No error message')}")
                    elif isinstance(messages, list):
                        for msg in messages:
                            if isinstance(msg, dict):
                                logger.info(f"- {msg.get('type', 'Unknown')}: {msg.get('error', 'No error message')}")
                
                return response_data
                
        except httpx.HTTPError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nResponse status: {e.response.status_code}"
                try:
                    error_details = e.response.json()
                    error_msg += f"\nError details: {json.dumps(error_details)}"
                except:
                    error_msg += f"\nResponse text: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Failed to get trip plan: {str(e)}")
            raise Exception(f"Failed to get trip plan: {str(e)}")
    
    def format_trip_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the raw API response into a more user-friendly structure
        
        Args:
            response: Raw API response
            
        Returns:
            Formatted trip information with:
            - journeys: List of journey options with calculated durations and delays
        """
        logger.info("Starting response formatting...")
        
        # Return empty list if no journey data
        if not response or "journeys" not in response:
            return {"journeys": []}
            
        journeys = []
        
        for journey in response.get("journeys", []):
            # Log raw journey data for debugging
            logger.debug(f"Processing journey data: {json.dumps(journey, indent=2)}")
            
            # Ensure time fields always have values and are converted to Sydney time
            start_time = journey.get("legs", [{}])[0].get("origin", {}).get("departureTimePlanned", "")
            end_time = journey.get("legs", [{}])[-1].get("destination", {}).get("arrivalTimePlanned", "")
            
            # Calculate total duration (including waiting and transfer times)
            duration = 0
            try:
                if start_time and end_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = int((end_dt - start_dt).total_seconds() / 60)
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not calculate duration: {e}")
            
            # Calculate waiting time until first transport
            waiting_time = None
            try:
                now = datetime.now(SYDNEY_TIMEZONE)
                first_leg = journey.get("legs", [{}])[0]
                first_departure = first_leg.get("origin", {}).get("departureTimeEstimated") or first_leg.get("origin", {}).get("departureTimePlanned")
                
                if first_departure:
                    departure_dt = datetime.fromisoformat(first_departure.replace('Z', '+00:00')).astimezone(SYDNEY_TIMEZONE)
                    # Calculate waiting time regardless of whether it's in the past or future
                    waiting_time = int((departure_dt - now).total_seconds() / 60)
                    if waiting_time > 0:
                        logger.debug(f"Next transport arrives in {waiting_time} minutes")
                    else:
                        logger.debug(f"Departure time has passed by {abs(waiting_time)} minutes")
                else:
                    logger.debug("Could not determine departure time for waiting time calculation")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not calculate waiting time: {e}")
                waiting_time = None
            
            formatted_journey = {
                "duration": duration,  # Total duration including waiting and transfer times
                "start_time": self._convert_to_sydney_time(start_time) or "Unknown",
                "end_time": self._convert_to_sydney_time(end_time) or "Unknown",
                "waiting_time": waiting_time,  # Time to wait until first transport arrives
                "legs": [],
                "stopSequence": []  # Initialize stop sequence list
            }
            
            # Process stop sequence for all legs
            for leg in journey.get("legs", []):
                # Process existing leg information
                transportation = leg.get("transportation", {})
                origin = leg.get("origin", {})
                destination = leg.get("destination", {})
                
                # Get stop sequence for this leg
                stops = leg.get("stopSequence", [])
                for stop in stops:
                    stop_info = {
                        "disassembledName": stop.get("disassembledName", ""),
                        "arrivalTimePlanned": self._convert_to_sydney_time(stop.get("arrivalTimePlanned"))
                    }
                    formatted_journey["stopSequence"].append(stop_info)
                
                # Continue with existing leg formatting
                # Get both planned and estimated times
                departure_planned = origin.get("departureTimePlanned")
                departure_estimated = origin.get("departureTimeEstimated")
                arrival_planned = destination.get("arrivalTimePlanned")
                arrival_estimated = destination.get("arrivalTimeEstimated")
                
                # Calculate departure delay
                departure_delay = None
                if departure_planned and departure_estimated:
                    try:
                        planned_dt = datetime.fromisoformat(departure_planned.replace('Z', '+00:00'))
                        estimated_dt = datetime.fromisoformat(departure_estimated.replace('Z', '+00:00'))
                        departure_delay = int((estimated_dt - planned_dt).total_seconds() / 60)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not calculate departure delay: {e}")
                
                # Calculate arrival delay
                arrival_delay = None
                if arrival_planned and arrival_estimated:
                    try:
                        planned_dt = datetime.fromisoformat(arrival_planned.replace('Z', '+00:00'))
                        estimated_dt = datetime.fromisoformat(arrival_estimated.replace('Z', '+00:00'))
                        arrival_delay = int((estimated_dt - planned_dt).total_seconds() / 60)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not calculate arrival delay: {e}")
                
                # Calculate actual duration for each leg (including potential waiting time)
                leg_duration = 0
                try:
                    leg_start = origin.get("departureTimePlanned")
                    leg_end = destination.get("arrivalTimePlanned")
                    if leg_start and leg_end:
                        leg_start_dt = datetime.fromisoformat(leg_start.replace('Z', '+00:00'))
                        leg_end_dt = datetime.fromisoformat(leg_end.replace('Z', '+00:00'))
                        leg_duration = int((leg_end_dt - leg_start_dt).total_seconds() / 60)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not calculate leg duration: {e}")
                
                formatted_leg = {
                    "mode": transportation.get("product", {}).get("name", "Unknown"),
                    "line": transportation.get("number", ""),
                    "duration": leg_duration,  # Actual duration for this leg
                    "origin": {
                        "name": origin.get("name", "Unknown"),
                        "departure_time": self._convert_to_sydney_time(
                            departure_estimated or departure_planned
                        ) if departure_estimated or departure_planned else None,
                        "arrival_time": self._convert_to_sydney_time(
                            origin.get("arrivalTimeEstimated") or origin.get("arrivalTimePlanned")
                        ) if origin.get("arrivalTimeEstimated") or origin.get("arrivalTimePlanned") else None,
                        "departure_delay": departure_delay,
                        "arrival_delay": None  # We don't calculate arrival delay for origin
                    },
                    "destination": {
                        "name": destination.get("name", "Unknown"),
                        "departure_time": self._convert_to_sydney_time(
                            destination.get("departureTimeEstimated") or destination.get("departureTimePlanned")
                        ) if destination.get("departureTimeEstimated") or destination.get("departureTimePlanned") else None,
                        "arrival_time": self._convert_to_sydney_time(
                            arrival_estimated or arrival_planned
                        ) if arrival_estimated or arrival_planned else None,
                        "departure_delay": None,  # We don't calculate departure delay for destination
                        "arrival_delay": arrival_delay
                    }
                }
                formatted_journey["legs"].append(formatted_leg)
            
            journeys.append(formatted_journey)
            
        formatted_response = {
            "journeys": journeys
        }
        
        logger.info(f"Response formatting completed. Processed {len(journeys)} journeys.")
        return formatted_response 