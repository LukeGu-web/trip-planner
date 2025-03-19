import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
from urllib.parse import urlencode

from app.core.config import settings
from app.services.opal_fare_service import OpalFareService
from app.services.station_translation_service import StationTranslationService
from app.utils.date_utils import (
    SYDNEY_TIMEZONE, 
    is_off_peak_time, 
    convert_to_sydney_time, 
    format_time
)
from app.utils.api_utils import make_api_request, filter_journeys_by_time

# Configure logging
logger = logging.getLogger(__name__)

class TfnswService:
    def __init__(self):
        self.base_url = settings.TFNSW_API_BASE_URL
        api_key = settings.TFNSW_API_KEY
        if not api_key:
            logger.error("TFNSW_API_KEY not set in environment variables")
            raise ValueError("TFNSW_API_KEY is required")
            
        self.headers = {
            "Authorization": f"apikey {api_key}",
            "Accept": "application/json"
        }
        self.opal_service = OpalFareService()
        self.translation_service = StationTranslationService()
        logger.debug(f"Initialized TfnswService with base URL: {self.base_url}")
    
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
        date_str, time_str = format_time(departure_time)
        
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
        
        logger.info(f"Requesting trip plan: from {from_location} to {to_location}")
        
        try:
            response_data = await make_api_request(
                self.base_url, 
                "trip", 
                self.headers, 
                params
            )
            
            # Filter journeys before reference time
            if "journeys" in response_data:
                journey_count = len(response_data.get("journeys", []))
                logger.debug(f"Received {journey_count} journeys")
                
                filtered_journeys = filter_journeys_by_time(
                    response_data["journeys"], 
                    departure_time
                )
                
                response_data["journeys"] = filtered_journeys
                logger.debug(f"After filtering, {len(filtered_journeys)} journeys remain")
            
            if len(response_data.get("journeys", [])) == 0:
                logger.warning("No journeys found. This might be due to no available services for the requested time period or route distance/complexity")
            
            return response_data
                
        except Exception as e:
            logger.error(f"Failed to get trip plan: {str(e)}")
            raise
    
    def format_trip_response(self, response: Dict[str, Any], language_code: str = "en") -> Dict[str, Any]:
        """
        Format the raw API response into a more user-friendly structure
        
        Args:
            response: Raw API response
            language_code: Language code for station name translations (default: "en")
            
        Returns:
            Formatted trip information with:
            - journeys: List of journey options with calculated durations and delays
        """
        logger.debug("Starting response formatting...")
        
        # Return empty list if no journey data
        if not response or "journeys" not in response:
            return {"journeys": []}
            
        journeys = []
        
        for journey in response.get("journeys", []):
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
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not calculate waiting time: {e}")
                waiting_time = None
            
            formatted_journey = {
                "duration": duration,  # Total duration including waiting and transfer times
                "start_time": convert_to_sydney_time(start_time),
                "end_time": convert_to_sydney_time(end_time),
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
                departure_time = departure_time.astimezone(SYDNEY_TIMEZONE)
                
                # Check if it's off-peak time
                is_off_peak = is_off_peak_time(departure_time)
                
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
            legs = journey.get("legs", [])
            for i, leg in enumerate(legs):
                transport_mode = leg.get("transportation", {}).get("product", {}).get("name", "Unknown")
                
                # 处理步行换乘路段
                if transport_mode.lower() == "footpath":
                    # 获取前后leg的交通工具类型
                    prev_mode = legs[i-1].get("transportation", {}).get("product", {}).get("name", "Unknown") if i > 0 else None
                    next_mode = legs[i+1].get("transportation", {}).get("product", {}).get("name", "Unknown") if i < len(legs)-1 else None
                    
                    # 翻译起点（使用前一个leg的交通工具类型）
                    origin_name = leg.get("origin", {}).get("name", "Unknown")
                    translated_origin = self.translation_service.translate_station_names(
                        origin_name, prev_mode or transport_mode, language_code
                    )
                    
                    # 翻译终点（使用后一个leg的交通工具类型）
                    destination_name = leg.get("destination", {}).get("name", "Unknown")
                    translated_destination = self.translation_service.translate_station_names(
                        destination_name, next_mode or transport_mode, language_code
                    )
                else:
                    # 正常交通工具路段的翻译
                    origin_name = leg.get("origin", {}).get("name", "Unknown")
                    destination_name = leg.get("destination", {}).get("name", "Unknown")
                    
                    translated_origin = self.translation_service.translate_station_names(
                        origin_name, transport_mode, language_code
                    )
                    translated_destination = self.translation_service.translate_station_names(
                        destination_name, transport_mode, language_code
                    )
                
                formatted_leg = {
                    "mode": transport_mode,
                    "line": leg.get("transportation", {}).get("disassembledName", "Unknown"),
                    "duration": leg.get("duration", 0),
                    "origin": {
                        "name": translated_origin,
                        "departure_time": convert_to_sydney_time(leg.get("origin", {}).get("departureTimePlanned")),
                        "arrival_time": convert_to_sydney_time(leg.get("origin", {}).get("arrivalTimePlanned")),
                        "departure_delay": leg.get("origin", {}).get("departureDelay", 0),
                        "arrival_delay": leg.get("origin", {}).get("arrivalDelay", 0)
                    },
                    "destination": {
                        "name": translated_destination,
                        "departure_time": convert_to_sydney_time(leg.get("destination", {}).get("departureTimePlanned")),
                        "arrival_time": convert_to_sydney_time(leg.get("destination", {}).get("arrivalTimePlanned")),
                        "departure_delay": leg.get("destination", {}).get("departureDelay", 0),
                        "arrival_delay": leg.get("destination", {}).get("arrivalDelay", 0)
                    }
                }
                formatted_journey["legs"].append(formatted_leg)
                
                # Add stop sequence if available
                if "stopSequence" in leg:
                    for stop in leg["stopSequence"]:
                        stop_name = stop.get("disassembledName", "Unknown")
                        translated_stop = self.translation_service.translate_station_names(
                            stop_name, transport_mode, language_code
                        )
                        formatted_stop = {
                            "disassembledName": translated_stop,
                            "arrivalTimePlanned": convert_to_sydney_time(stop.get("arrivalTimePlanned"))
                        }
                        formatted_journey["stopSequence"].append(formatted_stop)
            
            journeys.append(formatted_journey)
        
        logger.debug(f"Response formatting completed. Processed {len(journeys)} journeys.")
        return {"journeys": journeys} 