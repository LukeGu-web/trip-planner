import httpx
from app.core.config import settings
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from urllib.parse import urlencode
import json
import pytz

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# 设置悉尼时区
SYDNEY_TIMEZONE = pytz.timezone('Australia/Sydney')

class TfnswService:
    def __init__(self):
        self.base_url = settings.TFNSW_API_BASE_URL
        self.headers = {
            "Authorization": f"apikey {settings.TFNSW_API_KEY}",
            "Accept": "application/json"
        }
    
    def _format_time(self, time_str: Optional[str]) -> tuple[str, str]:
        """Format time string into date and time components"""
        if not time_str:
            now = SYDNEY_TIMEZONE.localize(datetime.now())
            return now.strftime("%Y%m%d"), now.strftime("%H%M")
        
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # 转换为悉尼时间
            sydney_dt = dt.astimezone(SYDNEY_TIMEZONE)
            return sydney_dt.strftime("%Y%m%d"), sydney_dt.strftime("%H%M")
        except ValueError as e:
            raise ValueError(f"Invalid time format. Expected ISO format (e.g., 2024-01-20T09:00:00): {e}")

    def _convert_to_sydney_time(self, time_str: str) -> str:
        """Convert UTC time string to Sydney time"""
        if not time_str or time_str == "Unknown":
            return time_str
        
        try:
            # 解析时间字符串（假设输入是UTC）
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # 转换为悉尼时间
            sydney_time = dt.astimezone(SYDNEY_TIMEZONE)
            # 返回格式化的时间字符串
            return sydney_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        except (ValueError, TypeError):
            return time_str
    
    async def get_trip_plan(self, 
                          from_location: str,
                          to_location: str,
                          departure_time: str = None,
                          arrival_time: str = None) -> Dict[str, Any]:
        """
        Get trip planning information from Transport for NSW API
        
        Args:
            from_location: Starting location (can be stop ID or coordinates)
            to_location: Destination location (can be stop ID or coordinates)
            departure_time: Optional departure time in ISO format
            arrival_time: Optional arrival time in ISO format
            
        Returns:
            Dict containing the trip planning response
        """
        # Use departure_time if provided, otherwise use arrival_time
        reference_time = departure_time or arrival_time
        date_str, time_str = self._format_time(reference_time)
        
        params = {
            "outputFormat": "rapidJSON",
            "coordOutputFormat": "EPSG:4326",
            "itdTripDate": date_str,
            "itdTripTime": time_str,
            "itdTimeDepArr": "dep" if departure_time else "arr",
            "type_origin": "stop",
            "name_origin": from_location,
            "type_destination": "stop",
            "name_destination": to_location,
            "calcNumberOfTrips": "5",
            "wheelchair": "false",
            "TfNSWSF": "true",
            "version": "10.2.1.42"
        }
        
        # 构建完整的请求URL用于日志记录
        full_url = f"{self.base_url}/trip?{urlencode(params)}"
        logger.info(f"Making request to Transport for NSW API:")
        logger.info(f"GET@{full_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/trip",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                
                response_data = response.json()
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Raw response data: {json.dumps(response_data, indent=2)}")
                return response_data
        except httpx.HTTPError as e:
            logger.error(f"HTTP request failed: {str(e)}")
            raise Exception(f"HTTP request failed: {str(e)}")
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
            - journeys: List of journey options
            - message: Status or information message
            - duration: Total journey time in minutes
        """
        logger.info("Starting response formatting...")
        
        # 检查API响应中的错误信息
        if "errorMessage" in response:
            return {
                "journeys": [],
                "message": response["errorMessage"],
            }
            
        if not response or "journeys" not in response:
            return {
                "journeys": [],
                "message": "No journeys found"
            }
            
        journeys = []
        
        for journey in response.get("journeys", []):
            logger.info(f"Processing journey: {json.dumps(journey, indent=2)}")
            
            # 确保时间字段始终有值并转换为悉尼时间
            start_time = journey.get("legs", [{}])[0].get("origin", {}).get("departureTimePlanned", "")
            end_time = journey.get("legs", [{}])[-1].get("destination", {}).get("arrivalTimePlanned", "")
            
            # 处理行程时长（分钟）
            duration = 0
            if "duration" in journey:
                try:
                    # 尝试直接从API响应中获取分钟数
                    duration = int(journey["duration"])
                except (ValueError, TypeError):
                    # 如果失败，尝试计算起止时间的差值
                    try:
                        if start_time and end_time:
                            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            duration = int((end_dt - start_dt).total_seconds() / 60)
                    except (ValueError, TypeError):
                        duration = 0
            
            logger.info(f"Calculated duration: {duration} minutes")
            
            formatted_journey = {
                "duration": duration,
                "start_time": self._convert_to_sydney_time(start_time) or "Unknown",
                "end_time": self._convert_to_sydney_time(end_time) or "Unknown",
                "legs": []
            }
            
            for leg in journey.get("legs", []):
                transportation = leg.get("transportation", {})
                origin = leg.get("origin", {})
                destination = leg.get("destination", {})
                
                formatted_leg = {
                    "mode": transportation.get("product", {}).get("name", "Unknown"),
                    "line": transportation.get("number", ""),
                    "origin": {
                        "name": origin.get("name", "Unknown"),
                        "departure_time": self._convert_to_sydney_time(
                            origin.get("departureTimePlanned", "Unknown")
                        ),
                        "arrival_time": self._convert_to_sydney_time(
                            origin.get("arrivalTimePlanned")
                        ) if origin.get("arrivalTimePlanned") else None
                    },
                    "destination": {
                        "name": destination.get("name", "Unknown"),
                        "departure_time": self._convert_to_sydney_time(
                            destination.get("departureTimePlanned")
                        ) if destination.get("departureTimePlanned") else None,
                        "arrival_time": self._convert_to_sydney_time(
                            destination.get("arrivalTimePlanned", "Unknown")
                        )
                    }
                }
                formatted_journey["legs"].append(formatted_leg)
            
            journeys.append(formatted_journey)
        
        # 构建响应消息
        message = None
        if response.get("messages"):
            messages = []
            for msg in response["messages"]:
                if isinstance(msg, dict) and "text" in msg:
                    messages.append(msg["text"])
                elif isinstance(msg, str):
                    messages.append(msg)
            message = "; ".join(messages) if messages else None
        
        if not message and response.get("status"):
            message = response["status"]
        
        if not message:
            message = "Trip plan retrieved successfully"
            
        logger.info(f"Final message: {message}")
            
        return {
            "journeys": journeys,
            "message": message
        } 