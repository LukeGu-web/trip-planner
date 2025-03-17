import json
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class OpalFareService:
    def __init__(self):
        self.distance_map = None
        self.load_distance_map()
        
        # 2024 July Opal fares for trains (in AUD)
        self.rail_fare_bands = {
            "0-10": 4.13,
            "10-20": 5.22,
            "20-35": 6.05,
            "35-65": 8.02,
            "65+": 10.34
        }
        
        # Access fee for stations (in AUD)
        self.station_access_fees = {
            "Airport": 15.40,  # Airport stations access fee
            "Domestic Airport": 15.40,
            "International Airport": 15.40,
            "Sydney Airport": 15.40,
            "Mascot": 15.40
        }
        
        # Off-peak discount (30% for trains)
        self.off_peak_discount = 0.30
    
    def load_distance_map(self):
        """Load the distance map from JSON file"""
        try:
            file_path = Path("app/data/distance_map.json")
            logger.debug(f"Loading distance map from: {file_path.absolute()}")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.distance_map = json.load(f)
            logger.info(f"Successfully loaded distance map with {len(self.distance_map)} entries")
        except Exception as e:
            logger.error(f"Failed to load distance map: {e}")
            raise
    
    def clean_station_name(self, station_name: str) -> str:
        """Clean station name by removing platform info and city/suburb names"""
        original_name = station_name
        # Remove platform information
        station_name = re.sub(r', Platform \d+', '', station_name)
        # Remove city/suburb names
        station_name = re.sub(r', [A-Za-z ]+$', '', station_name)
        # Remove "Station" suffix
        station_name = re.sub(r' Station$', '', station_name)
        logger.debug(f"Cleaned station name from '{original_name}' to '{station_name}'")
        return station_name
    
    def get_station_distance(self, origin: str, destination: str) -> float:
        """Get the distance between two stations"""
        try:
            # Clean station names
            clean_origin = self.clean_station_name(origin)
            clean_destination = self.clean_station_name(destination)
            
            logger.debug(f"Searching for distance between '{clean_origin}' and '{clean_destination}'")
            
            # Create key for distance map (stations sorted alphabetically)
            stations_sorted = tuple(sorted([clean_origin, clean_destination]))
            key = f"{stations_sorted[0]}->{stations_sorted[1]}"
            
            # Get distance from map
            if key not in self.distance_map:
                logger.warning(f"No distance found for key: {key}")
                return None
                
            distance = self.distance_map[key]
            logger.info(f"Found distance between {clean_origin} and {clean_destination}: {distance}km")
            return float(distance)
        except Exception as e:
            logger.error(f"Error finding distance between {clean_origin} and {clean_destination}: {e}")
            return None
    
    def get_fare_band(self, distance: float) -> str:
        """Get the fare band for a given distance"""
        logger.debug(f"Determining fare band for distance: {distance}km")
        if distance <= 10:
            band = "0-10"
        elif distance <= 20:
            band = "10-20"
        elif distance <= 35:
            band = "20-35"
        elif distance <= 65:
            band = "35-65"
        else:
            band = "65+"
        logger.debug(f"Selected fare band: {band}")
        return band
    
    def calculate_access_fee(self, station_name: str) -> float:
        """Calculate access fee for a station if applicable"""
        clean_station = self.clean_station_name(station_name)
        return self.station_access_fees.get(clean_station, 0.0)
    
    def calculate_fare(self, origin: str, destination: str, is_off_peak: bool = False) -> dict:
        """Calculate the Opal fare between two stations"""
        try:
            logger.info(f"Calculating fare from {origin} to {destination} (off-peak: {is_off_peak})")
            distance = self.get_station_distance(origin, destination)
            if distance is None:
                logger.warning(f"Could not calculate fare between {origin} and {destination} - distance not found")
                return None
            
            fare_band = self.get_fare_band(distance)
            base_fare = self.rail_fare_bands[fare_band]
            
            # Calculate off-peak fare with 30% discount
            off_peak_fare = None
            if is_off_peak:
                off_peak_fare = round(base_fare * (1 - self.off_peak_discount), 2)
            
            # Calculate access fees
            origin_access_fee = self.calculate_access_fee(origin)
            destination_access_fee = self.calculate_access_fee(destination)
            total_access_fee = origin_access_fee + destination_access_fee
            
            result = {
                "distance": distance,
                "fare_band": fare_band,
                "base_fare": base_fare,
                "off_peak_fare": off_peak_fare,
                "access_fee": total_access_fee,
                "total_fare": round(base_fare + total_access_fee, 2),
                "total_off_peak_fare": round(off_peak_fare + total_access_fee, 2) if is_off_peak else None
            }
            
            logger.info(f"Calculated fare for {origin} to {destination}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating fare: {e}")
            return None 