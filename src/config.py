"""Configuration management for DotaForge."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MatchSelectionConfig(BaseSettings):
    """Configuration for match selection criteria."""
    
    model_config = SettingsConfigDict(env_prefix="MATCH_SELECTION__")
    
    matches_per_day: int = Field(default=1, ge=1, le=10)
    only_wins: bool = False
    only_losses: bool = False
    hero_filter: Optional[str] = None
    min_duration_seconds: int = Field(default=600, ge=300)
    max_duration_seconds: int = Field(default=5400, le=7200)
    min_kda: float = Field(default=0.0, ge=0.0)
    sort_by: str = Field(default="date")
    
    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Ensure sort_by is a valid value."""
        valid = {"date", "kda", "duration"}
        if v not in valid:
            raise ValueError(f"sort_by must be one of: {valid}")
        return v
    
    @model_validator(mode="after")
    def validate_win_loss(self):
        """Ensure only_wins and only_losses aren't both True."""
        if self.only_wins and self.only_losses:
            raise ValueError("Cannot set both only_wins and only_losses to True")
        return self


class RecordingConfig(BaseSettings):
    """Configuration for video recording."""
    
    model_config = SettingsConfigDict(env_prefix="RECORDING__")
    
    resolution: str = Field(default="1920x1080")
    framerate: int = Field(default=60)
    quality: str = Field(default="high")
    crf: int = Field(default=18, ge=0, le=51)
    
    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        """Ensure resolution is in correct format."""
        try:
            width, height = v.split("x")
            int(width)
            int(height)
            return v
        except ValueError:
            raise ValueError(f"Invalid resolution format: {v}. Use WIDTHxHEIGHT (e.g., 1920x1080)")
    
    @field_validator("framerate")
    @classmethod
    def validate_framerate(cls, v: int) -> int:
        """Ensure framerate is valid."""
        valid = {30, 60, 120, 144, 240}
        if v not in valid:
            raise ValueError(f"framerate must be one of: {valid}")
        return v
    
    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: str) -> str:
        """Ensure quality is valid."""
        valid = {"low", "medium", "high", "lossless"}
        if v not in valid:
            raise ValueError(f"quality must be one of: {valid}")
        return v


class StorageConfig(BaseSettings):
    """Configuration for storage management."""
    
    model_config = SettingsConfigDict(env_prefix="STORAGE__")
    
    auto_delete_days: int = Field(default=10, ge=1)
    max_storage_gb: float = Field(default=100.0, ge=10.0)
    cleanup_replays: bool = True
    cleanup_temp: bool = True


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"  # Allow extra env vars without error
    )
    
    # Player settings
    steam_account_id: str = Field(..., description="Steam Account ID (32-bit)")
    player_name: str = Field(default="Player")
    
    # OpenDota
    opendota_api_key: Optional[str] = None
    
    # Dota 2 path (optional, will auto-detect)
    dota2_path: Optional[Path] = None
    
    # Schedule
    run_time: str = Field(default="02:00")
    timezone: str = Field(default="UTC")
    
    # Timeouts and retries
    max_retries: int = Field(default=3, ge=1)
    retry_delay_seconds: int = Field(default=60, ge=1)
    dota_load_timeout: int = Field(default=120, ge=30)
    
    # Debugging
    debug: bool = False
    dry_run: bool = False
    
    # Nested configs
    match_selection: MatchSelectionConfig = Field(default_factory=MatchSelectionConfig)
    recording: RecordingConfig = Field(default_factory=RecordingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    
    @field_validator("run_time")
    @classmethod
    def validate_run_time(cls, v: str) -> str:
        """Ensure run_time is in HH:MM format."""
        try:
            hours, minutes = v.split(":")
            h, m = int(hours), int(minutes)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return v
        except ValueError:
            raise ValueError(f"Invalid run_time: {v}. Use 24-hour format (e.g., 02:00)")
    
    @field_validator("dota2_path")
    @classmethod
    def validate_dota2_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate Dota 2 path if provided."""
        if v is None:
            return v
        v = Path(v)
        if not v.exists():
            raise ValueError(f"Dota 2 path does not exist: {v}")
        # Check for game/bin/win64/dota2.exe
        exe = v / "game/bin/win64/dota2.exe"
        if not exe.exists():
            raise ValueError(f"Dota 2 executable not found at: {exe}")
        return v


# Global settings instance - initialized lazily
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance.
    
    Raises:
        ValidationError: If required environment variables are not set
    """
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
        except Exception as e:
            # Provide helpful error message
            import sys
            print(f"\n{'='*60}")
            print("ERROR: Failed to load settings")
            print(f"{'='*60}")
            print(f"\n{e}")
            print("\nPlease ensure you have:")
            print("  1. Created a .env file (copy from .env.example)")
            print("  2. Set the STEAM_ACCOUNT_ID variable")
            print(f"\n{'='*60}\n")
            sys.exit(1)
    return _settings


# Convenience accessor - will be initialized on first use
settings: Settings = None  # type: ignore


def reload_settings():
    """Reload settings from .env file."""
    global _settings, settings
    _settings = Settings()
    settings = _settings
