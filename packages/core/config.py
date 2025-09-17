"""Core configuration module using Pydantic Settings."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = Field(default="sqlite:///./trading.db")


class AlpacaConfig(BaseModel):
    """Alpaca trading configuration."""
    api_key: str = Field(default="")
    secret_key: str = Field(default="")
    base_url: str = Field(default="https://paper-api.alpaca.markets")
    paper_mode: bool = Field(default=True)


class AWSConfig(BaseModel):
    """AWS configuration."""
    region: str = Field(default="us-east-1")
    access_key_id: Optional[str] = Field(default=None)
    secret_access_key: Optional[str] = Field(default=None)
    s3_bucket: str = Field(default="algorithmic-trader-artifacts")
    s3_prefix: str = Field(default="artifacts")


class TradingConfig(BaseModel):
    """Trading configuration."""
    dry_run: bool = Field(default=True)
    max_position_size_pct: float = Field(default=2.0)
    daily_loss_limit_pct: float = Field(default=5.0)
    stop_loss_atr_multiplier: float = Field(default=1.5)
    take_profit_atr_multiplier: float = Field(default=3.0)


class ScreeningConfig(BaseModel):
    """Screening configuration."""
    min_price: float = Field(default=1.0)
    max_price: float = Field(default=1000.0)
    min_dollar_volume: int = Field(default=10_000_000)
    min_atr_percent: float = Field(default=2.0)
    max_symbols_per_sector: int = Field(default=5)
    topk_symbols: int = Field(default=50)


class TimeConfig(BaseModel):
    """Time configuration."""
    trading_start_time: str = Field(default="09:30")
    trading_end_time: str = Field(default="16:00")
    premarket_start_time: str = Field(default="07:00")
    afterhours_end_time: str = Field(default="20:00")
    timezone: str = Field(default="America/New_York")


class UIConfig(BaseModel):
    """UI configuration."""
    mode: str = Field(default="artifacts")  # artifacts | live
    password: str = Field(default="changeme")
    artifacts_root: str = Field(default="artifacts")
    refresh_seconds: int = Field(default=30)


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )
    
    # Core settings
    debug: bool = Field(default=False)
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    
    # Feature flags
    provider_yahoo_enabled: bool = Field(default=True)
    provider_tradingview_enabled: bool = Field(default=False)
    feature_tv: bool = Field(default=False)
    feature_live_providers: bool = Field(default=False)
    enable_paper_trade: bool = Field(default=True)
    metrics_enabled: bool = Field(default=True)
    
    # Configuration sections
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    alpaca: AlpacaConfig = Field(default_factory=AlpacaConfig)
    aws: AWSConfig = Field(default_factory=AWSConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    screening: ScreeningConfig = Field(default_factory=ScreeningConfig)
    time: TimeConfig = Field(default_factory=TimeConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # Paths
    artifacts_root: str = Field(default="artifacts")
    config_root: str = Field(default="config")
    
    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent
    
    @property
    def artifacts_path(self) -> Path:
        """Get the artifacts directory path."""
        return self.project_root / self.artifacts_root
    
    @property
    def config_path(self) -> Path:
        """Get the config directory path."""
        return self.project_root / self.config_root
    
    def model_post_init(self, __context) -> None:
        """Post-initialization setup."""
        # Create artifacts directory if it doesn't exist
        self.artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # Load environment-specific overrides
        env_file = self.config_path / f".env.{self.environment}"
        if env_file.exists():
            # Re-parse with environment-specific file
            pass


# Global settings instance
settings = Settings()

# Export commonly used configs
database_config = settings.database
alpaca_config = settings.alpaca
aws_config = settings.aws
trading_config = settings.trading
screening_config = settings.screening
time_config = settings.time
ui_config = settings.ui
