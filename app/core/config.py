from pydantic_settings import BaseSettings
from typing import Optional
import logging

def get_log_level(log_level: str) -> int:
    """Convert string log level to logging constant"""
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return levels.get(log_level.upper(), logging.INFO)

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Trip Planner BFF"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Transport for NSW API Settings
    TFNSW_API_KEY: str
    TFNSW_API_BASE_URL: str = "https://api.transport.nsw.gov.au/v1/tp"
    
    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Security Settings
    SECRET_KEY: str = "your_secret_key_here"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def log_level(self) -> int:
        """Get the logging level as an integer constant"""
        return get_log_level(self.LOG_LEVEL)

settings = Settings() 