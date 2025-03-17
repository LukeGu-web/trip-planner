"""
NSW Public Holidays data for multiple years
"""

# NSW Public Holidays 2024
PUBLIC_HOLIDAYS_2024 = {
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
PUBLIC_HOLIDAYS_2025 = {
    "New Year's Day": "2025-01-01",
    "Australia Day": "2025-01-27",  # Monday after Australia Day (26th falls on Sunday)
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

# NSW Public Holidays 2026
PUBLIC_HOLIDAYS_2026 = {
    "New Year's Day": "2026-01-01",
    "Australia Day": "2026-01-26",
    "Good Friday": "2026-04-03",
    "Easter Saturday": "2026-04-04",
    "Easter Sunday": "2026-04-05",
    "Easter Monday": "2026-04-06",
    "Anzac Day": "2026-04-25",
    "King's Birthday": "2026-06-08",
    "Labour Day": "2026-10-05",
    "Christmas Day": "2026-12-25",
    "Boxing Day": "2026-12-28"  # Additional day (Boxing Day falls on Saturday)
}

# NSW Public Holidays 2027
PUBLIC_HOLIDAYS_2027 = {
    "New Year's Day": "2027-01-01",
    "Australia Day": "2027-01-26",
    "Good Friday": "2027-03-26",
    "Easter Saturday": "2027-03-27",
    "Easter Sunday": "2027-03-28",
    "Easter Monday": "2027-03-29",
    "Anzac Day": "2027-04-25",
    "Anzac Day Holiday": "2027-04-26",  # Additional day (Anzac Day falls on Sunday)
    "King's Birthday": "2027-06-14",
    "Labour Day": "2027-10-04",
    "Christmas Day": "2027-12-25",
    "Christmas Day Holiday": "2027-12-27", # Additional day (Christmas Day falls on Saturday)
    "Boxing Day": "2027-12-26",
    "Boxing Day Holiday": "2027-12-28"  # Additional day (Boxing Day falls on Sunday)
}

# Dictionary mapping years to their holiday dictionaries
HOLIDAYS_BY_YEAR = {
    2024: PUBLIC_HOLIDAYS_2024,
    2025: PUBLIC_HOLIDAYS_2025,
    2026: PUBLIC_HOLIDAYS_2026,
    2027: PUBLIC_HOLIDAYS_2027
}

def get_holidays_for_year(year: int) -> dict:
    """
    Get the public holidays dictionary for a specific year
    
    Args:
        year: The year to get holidays for
        
    Returns:
        Dictionary of holidays for the year or empty dict if not available
    """
    return HOLIDAYS_BY_YEAR.get(year, {}) 