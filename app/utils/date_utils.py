import pytz
from datetime import datetime
import logging
from typing import Optional, Tuple

from app.utils.public_holidays import (
    get_holidays_for_year, 
    HOLIDAYS_BY_YEAR
)

# Configure logging
logger = logging.getLogger(__name__)

# Set Sydney timezone
SYDNEY_TIMEZONE = pytz.timezone('Australia/Sydney')

def format_time(time_str: Optional[str]) -> Tuple[str, str]:
    """
    Format time string into date and time components
    
    Args:
        time_str: ISO format time string, or None to use current time
        
    Returns:
        Tuple containing formatted date and time (YYYYMMDD, HHMM)
    """
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

def convert_to_sydney_time(time_str: str) -> str:
    """
    Convert UTC time string to Sydney time
    
    Args:
        time_str: UTC time string
        
    Returns:
        Formatted Sydney time string
    """
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

def is_public_holiday(dt: datetime) -> bool:
    """
    Check if the given date is a public holiday in NSW
    
    Args:
        dt: Datetime to check (should be in Sydney timezone)
        
    Returns:
        True if the date is a public holiday, False otherwise
    """
    # Format date as YYYY-MM-DD
    date_str = dt.strftime("%Y-%m-%d")
    
    # Get holidays for the specific year
    year = dt.year
    holidays = get_holidays_for_year(year)
    
    # Check if date is in holidays
    if date_str in holidays.values():
        logger.debug(f"Date {date_str} is a public holiday in {year}")
        return True
    
    logger.debug(f"Date {date_str} is not a public holiday")
    return False

def is_off_peak_time(dt: datetime) -> bool:
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
    # First check if it's a public holiday
    if is_public_holiday(dt):
        logger.debug(f"Date {dt.strftime('%Y-%m-%d')} is a public holiday - off-peak applies")
        return True
        
    weekday = dt.weekday()  # Monday is 0, Sunday is 6
    hour = dt.hour
    minute = dt.minute
    
    # Weekend (Saturday = 5, Sunday = 6)
    if weekday >= 5:
        logger.debug(f"Day is weekend (weekday={weekday}) - off-peak applies")
        return True
        
    # Friday is all off-peak
    if weekday == 4:  # Friday
        logger.debug(f"Day is Friday - off-peak applies")
        return True
        
    # Monday to Thursday peak times
    # Morning peak: 6:30 AM to 10:00 AM
    if (hour == 6 and minute >= 30) or (hour > 6 and hour < 10):
        logger.debug(f"Time {hour}:{minute:02d} is during morning peak (6:30-10:00) on weekday {weekday}")
        return False
        
    # Evening peak: 3:00 PM to 7:00 PM
    if hour >= 15 and hour < 19:
        logger.debug(f"Time {hour}:{minute:02d} is during evening peak (15:00-19:00) on weekday {weekday}")
        return False
        
    # All other times are off-peak
    logger.debug(f"Time {hour}:{minute:02d} on weekday {weekday} is outside peak hours - off-peak applies")
    return True 