# config.py
from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Credentials for Darey API
    darey_username: SecretStr
    darey_password: SecretStr
    business_id: SecretStr

    # Origin Email Details
    origin_email: SecretStr
    origin_name: SecretStr

    # Mailjet
    mailjet_api_key: SecretStr
    mailjet_api_secret: SecretStr

    # Download options
    download_url: AnyHttpUrl
    download_limit: int = 50000
    batch_size: int = 500

    # Learner filtering
    inactive_days: int = 14
    low_score_threshold: int = 50

    # Retry / concurrency
    max_retries: int = 3
    retry_delay: int = 5  # seconds between retries

    # Test mode settings
    test_mode: bool = False
    test_email_address: str | None = None


# Global settings instance
# Pylance may warn, but it loads from .env
settings = Settings()  # type: ignore
