"""Match data models for DotaForge."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Match:
    """Represents a Dota 2 match for recording."""
    
    match_id: int
    player_slot: int
    hero_id: int
    hero_name: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    duration_seconds: int = 0
    radiant_win: bool = False
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    gpm: int = 0
    xpm: int = 0
    replay_url: Optional[str] = None
    
    @property
    def is_win(self) -> bool:
        """Check if the player won this match."""
        is_radiant = self.player_slot < 128
        return is_radiant == self.radiant_win
    
    @property
    def kda(self) -> float:
        """Calculate KDA ratio."""
        if self.deaths == 0:
            return float(self.kills + self.assists)
        return round((self.kills + self.assists) / self.deaths, 2)
    
    @property
    def duration_formatted(self) -> str:
        """Format duration as MM:SS."""
        mins = self.duration_seconds // 60
        secs = self.duration_seconds % 60
        return f"{mins}m {secs:02d}s"
    
    @property
    def dotabuff_url(self) -> str:
        """Generate Dotabuff match URL."""
        return f"https://www.dotabuff.com/matches/{self.match_id}"
    
    @property
    def opendota_url(self) -> str:
        """Generate OpenDota match URL."""
        return f"https://www.opendota.com/matches/{self.match_id}"
    
    def __repr__(self) -> str:
        return (f"Match({self.match_id}, {self.hero_name or 'Unknown'}, "
                f"KDA={self.kda}, {self.duration_formatted}, "
                f"{'Win' if self.is_win else 'Loss'})")


@dataclass
class ProcessedMatch:
    """Record of a processed match in the database."""
    
    match_id: int
    recorded_at: datetime
    video_path: Path
    status: str  # "success", "failed", "skipped"
    error_message: Optional[str] = None
    hero_name: Optional[str] = None
    kda: float = 0.0
    is_win: bool = False


@dataclass
class HeroInfo:
    """Hero information from OpenDota API."""
    
    id: int
    name: str
    localized_name: str
    img_url: Optional[str] = None
    icon_url: Optional[str] = None
