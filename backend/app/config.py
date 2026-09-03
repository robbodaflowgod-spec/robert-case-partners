# app/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Explicitly telling VS Code these attributes are part of the class schema
    PROJECT_NAME: str = "Robert Case & Partners Backend Engine"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # Required configurations (Pydantic will pull these dynamically from your .env)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Fixed: Adding a fallback or letting type hinting know it's a required string
    DATABASE_URL: str

   # This automatically searches for the .env file dynamically in the app's parent folders
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "../../.env"],
        extra="ignore"
    )

# Instantiate the settings object
settings = Settings()  # type: ignore
