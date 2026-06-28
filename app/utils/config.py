"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str = ""
    # Must use "google_genai:model" prefix — how create_deep_agent resolves the provider
    model_name: str = "google_genai:gemini-flash-latest"
    temperature: float = 0.2
    pdf_path: str = "data/rahul_technologies_corporate_report.pdf"
    excel_path: str = "data/Rahul_Technologies_Monthly_Production_and_Sales_2020_2025(1).xlsx"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def inject_env(self):
        """Inject GOOGLE_API_KEY into os.environ — create_deep_agent reads it from there."""
        if self.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.google_api_key


@lru_cache()
def get_settings() -> Settings:
    return Settings()
