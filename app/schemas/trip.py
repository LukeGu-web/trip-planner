from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Location(BaseModel):
    name: str = "Unknown"
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None

class TripLeg(BaseModel):
    mode: str = "Unknown"
    line: Optional[str] = None
    origin: Location
    destination: Location

class Journey(BaseModel):
    duration: int = Field(ge=0)
    start_time: str = "Unknown"
    end_time: str = "Unknown"
    legs: List[TripLeg]

class TripResponse(BaseModel):
    journeys: List[Journey] = []
    message: Optional[str] = None

class TripRequest(BaseModel):
    from_location: str = Field(..., description="Starting location")
    to_location: str = Field(..., description="Destination location")
    departure_time: Optional[str] = Field(None, description="Departure time in ISO format (e.g., 2024-01-20T09:00:00)")
    arrival_time: Optional[str] = Field(None, description="Arrival time in ISO format (e.g., 2024-01-20T09:00:00)")

    def validate_times(self) -> None:
        """Validate time formats and logic"""
        if self.departure_time and self.arrival_time:
            raise ValueError("Cannot specify both departure_time and arrival_time")
            
        for time_str in [self.departure_time, self.arrival_time]:
            if time_str:
                try:
                    datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError("Time must be in ISO format (e.g., 2024-01-20T09:00:00)") 