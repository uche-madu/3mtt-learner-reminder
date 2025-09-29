# config.py
from pathlib import Path
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
    origin_name: str

    # Mailjet
    mailjet_api_key: SecretStr
    mailjet_api_secret: SecretStr

    # SMTP / SES Settings
    email_host: str
    email_region: str
    email_port: int
    email_use_tls: bool
    email_host_user: SecretStr
    email_host_password: SecretStr
    use_smtp: bool = True  # If False, use SES API

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
    test_mode: bool
    test_email_address: str
    test_mode_count: int  # Limit learners per template in test mode
    concurrency: int  # For sending emails
    dry_run: bool = False  # If True, do not send any emails

    # Data directory
    data_dir: Path = Path(__file__).resolve().parent / "data"


# Global settings instance
# Pylance may warn, but it loads from .env
settings = Settings()  # type: ignore
