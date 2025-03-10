from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Location(BaseModel):
    name: str = "Unknown"
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    departure_delay: Optional[int] = None  # Delay in minutes for departure, positive means delayed
    arrival_delay: Optional[int] = None    # Delay in minutes for arrival, positive means delayed

class TripLeg(BaseModel):
    mode: str = "Unknown"
    line: Optional[str] = None
    duration: int = 0  # Duration in minutes
    origin: Location
    destination: Location

class StopSequence(BaseModel):
    disassembledName: str
    arrivalTimePlanned: Optional[str] = None

class Journey(BaseModel):
    journey_id: str = Field(..., description="Unique identifier for the journey")
    duration: int = Field(ge=0, description="Total journey duration in minutes")
    start_time: str
    end_time: str
    waiting_time: Optional[int] = Field(None, description="Time to wait until the first transport arrives (in minutes)")
    legs: List[TripLeg]
    stopSequence: List[StopSequence] = []  # Add stop sequence to Journey

class TripResponse(BaseModel):
    journeys: List[Journey] = []

class TripRequest(BaseModel):
    from_location: str = Field(..., description="Starting location")
    to_location: str = Field(..., description="Destination location")
    departure_time: Optional[str] = Field(None, description="Reference time in ISO format (e.g., 2024-03-20T09:00:00)")

    def validate_request(self) -> None:
        """Validate request parameters"""
        # Validate time format if provided
        if self.departure_time:
            try:
                datetime.fromisoformat(self.departure_time.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Time must be in ISO format (e.g., 2024-03-20T09:00:00)") 