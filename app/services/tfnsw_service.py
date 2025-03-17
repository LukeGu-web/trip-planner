import httpx
from app.core.config import settings
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from urllib.parse import urlencode
import json
import pytz
from app.services.opal_fare_service import OpalFareService

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
        self.opal_service = OpalFareService()
        logger.debug(f"Initialized TfnswService with base URL: {self.base_url}")
        
        # NSW Public Holidays 2024
        self.public_holidays_2024 = {
            "New Year's Day": "2024-01-01",
            "Australia Day": "2024-01-26",
            "Good Friday": "2024-03-29",
            "Easter Saturday": "2024-03-30",
            "Easter Sunday": "2024-03-31",
            "Easter Monday": "2024-04-01",
            "Anzac Day": "2024-04-25",
            "King's Birthday": "2024-06-10",
            "Labour Day": "2024-10-07",
            "Christmas Day": "2024-12-25",
            "Boxing Day": "2024-12-26"
        }
        
        # NSW Public Holidays 2025
        self.public_holidays_2025 = {
            "New Year's Day": "2025-01-01",
            "Australia Day": "2025-01-27",
            "Good Friday": "2025-04-18",
            "Easter Saturday": "2025-04-19",
            "Easter Sunday": "2025-04-20",
            "Easter Monday": "2025-04-21",
            "Anzac Day": "2025-04-25",
            "King's Birthday": "2025-06-09",
            "Labour Day": "2025-10-06",
            "Christmas Day": "2025-12-25",
            "Boxing Day": "2025-12-26"
        }
    
    def _format_time(self, time_str: Optional[str]) -> tuple[str, str]:
        """Format time string into date and time components"""
        if not time_str:
            now = datetime.now(SYDNEY_TIMEZONE)
            return now.strftime("%Y%m%d"), now.strftime("%H%M")
        
        try:
            # Parse the input time string
            dt = datetime.fromisoformat(time_str)
            # If the datetime is naive (no timezone info), assume it's Sydney time
            if dt.tzinfo is None:
                dt = SYDNEY_TIMEZONE.localize(dt)
            # Convert to Sydney time if it's in a different timezone
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
    
    def _is_public_holiday(self, dt: datetime) -> bool:
        """
        Check if the given date is a public holiday in NSW
        
        Args:
            dt: Datetime to check (should be in Sydney timezone)
            
        Returns:
            True if the date is a public holiday, False otherwise
        """
        # Format date as YYYY-MM-DD
        date_str = dt.strftime("%Y-%m-%d")
        
        # Check in both 2024 and 2025 holiday lists
        if date_str in self.public_holidays_2024.values() or date_str in self.public_holidays_2025.values():
            logger.debug(f"Date {date_str} is a public holiday")
            return True
            
        logger.debug(f"Date {date_str} is not a public holiday")
        return False
    
    def _is_off_peak_time(self, dt: datetime) -> bool:
        """
        Check if the given time is during off-peak hours in Sydney
        
        Peak hours are:
        - Monday to Thursday:
          - Morning peak: 6:30 AM to 10:00 AM
          - Evening peak: 3:00 PM to 7:00 PM
        - Friday: All day is off-peak
        - Weekends: All day is off-peak
        - Public holidays: All day is off-peak
        
        Args:
            dt: Datetime to check (should be in Sydney timezone)
            
        Returns:
            True if the time is off-peak, False if it's peak time
        """
        # Check if it's a public holiday first
        if self._is_public_holiday(dt):
            logger.info(f"Date {dt.strftime('%Y-%m-%d')} is a public holiday - off-peak applies")
            return True
            
        weekday = dt.weekday()  # Monday is 0, Sunday is 6
        hour = dt.hour
        minute = dt.minute
        
        # Weekend (Saturday = 5, Sunday = 6)
        if weekday >= 5:
            logger.info(f"Day is weekend (weekday={weekday}) - off-peak applies")
            return True
            
        # Friday is all off-peak
        if weekday == 4:  # Friday
            logger.info(f"Day is Friday - off-peak applies")
            return True
            
        # Monday to Thursday peak times
        # Morning peak: 6:30 AM to 10:00 AM
        if (hour == 6 and minute >= 30) or (hour > 6 and hour < 10):
            logger.info(f"Time {hour}:{minute:02d} is during morning peak (6:30-10:00) on weekday {weekday}")
            return False
            
        # Evening peak: 3:00 PM to 7:00 PM
        if hour >= 15 and hour < 19:
            logger.info(f"Time {hour}:{minute:02d} is during evening peak (15:00-19:00) on weekday {weekday}")
            return False
            
        # All other times are off-peak
        logger.info(f"Time {hour}:{minute:02d} on weekday {weekday} is outside peak hours - off-peak applies")
        return True
    
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
                        # Parse the input time string
                        reference_dt = datetime.fromisoformat(departure_time)
                        # If the datetime is naive (no timezone info), assume it's Sydney time
                        if reference_dt.tzinfo is None:
                            reference_dt = SYDNEY_TIMEZONE.localize(reference_dt)
                    else:
                        reference_dt = datetime.now(SYDNEY_TIMEZONE)
                    
                    filtered_journeys = []
                    for journey in response_data["journeys"]:
                        if journey.get("legs"):
                            first_leg = journey["legs"][0]
                            departure_time = first_leg.get("origin", {}).get("departureTimePlanned")
                            if departure_time:
                                journey_dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                                journey_dt = journey_dt.astimezone(SYDNEY_TIMEZONE)
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
                "start_time": self._convert_to_sydney_time(start_time),
                "end_time": self._convert_to_sydney_time(end_time),
                "waiting_time": waiting_time,
                "legs": [],
                "stopSequence": []
            }
            
            # Calculate fare if it's a train journey
            if any(leg.get("transportation", {}).get("product", {}).get("class") in [1, 2] for leg in journey.get("legs", [])):
                origin_station = journey["legs"][0]["origin"]["name"]
                destination_station = journey["legs"][-1]["destination"]["name"]
                
                # Check if the journey is during off-peak hours
                departure_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                sydney_tz = pytz.timezone('Australia/Sydney')
                departure_time = departure_time.astimezone(sydney_tz)
                
                # Check if journey is during off-peak hours
                is_off_peak = self._is_off_peak_time(departure_time)
                logger.debug(f"Is off-peak: {is_off_peak}")
                
                # Calculate fare
                fee_info = self.opal_service.calculate_fare(origin_station, destination_station, is_off_peak)
                
                if fee_info:
                    # Use off-peak fare if it's off-peak time
                    formatted_journey["fee"] = fee_info["total_off_peak_fare"] if is_off_peak else fee_info["total_fare"]
                    formatted_journey["is_off_peak"] = is_off_peak
                    formatted_journey["base_fare"] = fee_info["base_fare"]
                    formatted_journey["access_fee"] = fee_info["access_fee"]
                else:
                    formatted_journey["fee"] = None
                    formatted_journey["is_off_peak"] = None
                    formatted_journey["base_fare"] = None
                    formatted_journey["access_fee"] = None
            else:
                formatted_journey["fee"] = None
                formatted_journey["is_off_peak"] = None
                formatted_journey["base_fare"] = None
                formatted_journey["access_fee"] = None
            
            # Process each leg of the journey
            for leg in journey.get("legs", []):
                formatted_leg = {
                    "mode": leg.get("transportation", {}).get("product", {}).get("name", "Unknown"),
                    "line": leg.get("transportation", {}).get("disassembledName", "Unknown"),
                    "duration": leg.get("duration", 0),
                    "origin": {
                        "name": leg.get("origin", {}).get("name", "Unknown"),
                        "departure_time": self._convert_to_sydney_time(leg.get("origin", {}).get("departureTimePlanned")),
                        "arrival_time": self._convert_to_sydney_time(leg.get("origin", {}).get("arrivalTimePlanned")),
                        "departure_delay": leg.get("origin", {}).get("departureDelay", 0),
                        "arrival_delay": leg.get("origin", {}).get("arrivalDelay", 0)
                    },
                    "destination": {
                        "name": leg.get("destination", {}).get("name", "Unknown"),
                        "departure_time": self._convert_to_sydney_time(leg.get("destination", {}).get("departureTimePlanned")),
                        "arrival_time": self._convert_to_sydney_time(leg.get("destination", {}).get("arrivalTimePlanned")),
                        "departure_delay": leg.get("destination", {}).get("departureDelay", 0),
                        "arrival_delay": leg.get("destination", {}).get("arrivalDelay", 0)
                    }
                }
                formatted_journey["legs"].append(formatted_leg)
                
                # Add stop sequence if available
                if "stopSequence" in leg:
                    for stop in leg["stopSequence"]:
                        formatted_stop = {
                            "disassembledName": stop.get("disassembledName", "Unknown"),
                            "arrivalTimePlanned": self._convert_to_sydney_time(stop.get("arrivalTimePlanned"))
                        }
                        formatted_journey["stopSequence"].append(formatted_stop)
            
            journeys.append(formatted_journey)
        
        logger.info(f"Response formatting completed. Processed {len(journeys)} journeys.")
        return {"journeys": journeys} 