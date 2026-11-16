import os
from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Entry AI Service"
    port: int = 8000
    host: str = "0.0.0.0"
    environment: str = "development"
    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:5173",
    ]
    jwt_secret: str = "your-super-secret-jwt-key-change-this-in-production"
    mongodb_uri: str = "mongodb://localhost:27017/tishrei-entry"
    mongodb_db_name: str = "tishrei-entry"
    node_backend_url: str = "http://localhost:3001"
    ai_provider: str = "gemini"
    ai_model: str = "gemini/gemini-2.0-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def get_cors_origins(self) -> List[str]:
        origins = list(self.cors_origins) if isinstance(self.cors_origins, list) else []
        if self.environment == "development":
            dev_defaults = [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:5173",
            ]
            for dev_origin in dev_defaults:
                if dev_origin not in origins:
                    origins.append(dev_origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
