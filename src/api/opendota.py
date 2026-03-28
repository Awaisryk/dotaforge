"""OpenDota API client for fetching match data."""

from datetime import datetime
from typing import List, Optional, Dict

import httpx

from src.config import get_settings
from src.exceptions import OpenDotaError
from src.logger import logger
from src.models.match import Match, HeroInfo


class OpenDotaClient:
    """Client for interacting with the OpenDota API.
    
    Free tier allows 60 calls per minute without API key.
    With API key, higher rate limits are available.
    """
    
    BASE_URL = "https://api.opendota.com/api"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client.
        
        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key or get_settings().opendota_api_key
        self._hero_cache: Optional[Dict[int, HeroInfo]] = None
        
        # Create async HTTP client
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={
                "User-Agent": "DotaForge/1.0",
                "Accept": "application/json",
            },
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make an authenticated request to the API.
        
        Args:
            endpoint: API endpoint path (without base URL)
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            OpenDotaError: If the request fails
        """
        params = params or {}
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = await self._client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(
                "OpenDota API error",
                endpoint=endpoint,
                status_code=e.response.status_code,
                response=e.response.text[:200]
            )
            raise OpenDotaError(
                f"API error {e.response.status_code}: {e.response.text[:200]}"
            ) from e
        
        except httpx.RequestError as e:
            logger.error(
                "OpenDota request failed",
                endpoint=endpoint,
                error=str(e)
            )
            raise OpenDotaError(f"Request failed: {e}") from e
    
    async def get_heroes(self) -> Dict[int, HeroInfo]:
        """Fetch and cache all heroes.
        
        Returns:
            Dictionary mapping hero_id to HeroInfo
        """
        if self._hero_cache is not None:
            return self._hero_cache
        
        logger.info("Fetching heroes from OpenDota")
        
        data = await self._make_request("/heroes")
        
        self._hero_cache = {}
        for hero_data in data:
            hero = HeroInfo(
                id=hero_data["id"],
                name=hero_data.get("name", ""),
                localized_name=hero_data.get("localized_name", "Unknown"),
                img_url=f"https://cdn.cloudflare.steamstatic.com{hero_data['img']}" if hero_data.get("img") else None,
                icon_url=f"https://cdn.cloudflare.steamstatic.com{hero_data['icon']}" if hero_data.get("icon") else None
            )
            self._hero_cache[hero.id] = hero
        
        logger.info(f"Cached {len(self._hero_cache)} heroes")
        return self._hero_cache
    
    async def get_recent_matches(self, account_id: str) -> List[Match]:
        """Fetch recent matches for a player.
        
        Args:
            account_id: Steam account ID (32-bit)
            
        Returns:
            List of Match objects
            
        Raises:
            OpenDotaError: If the API request fails
        """
        logger.info("Fetching recent matches", account_id=account_id)
        
        data = await self._make_request(f"/players/{account_id}/recentMatches")
        
        if not data:
            logger.warning("No recent matches found", account_id=account_id)
            return []
        
        # Get hero cache for names
        heroes = await self.get_heroes()
        
        matches = []
        for match_data in data:
            hero_id = match_data["hero_id"]
            hero_info = heroes.get(hero_id)
            
            match = Match(
                match_id=match_data["match_id"],
                player_slot=match_data["player_slot"],
                hero_id=hero_id,
                hero_name=hero_info.localized_name if hero_info else None,
                start_time=datetime.fromtimestamp(match_data["start_time"]),
                duration_seconds=match_data["duration"],
                radiant_win=match_data["radiant_win"],
                kills=match_data["kills"],
                deaths=match_data["deaths"],
                assists=match_data["assists"],
                gpm=match_data["gold_per_min"],
                xpm=match_data["xp_per_min"],
                replay_url=None  # Will be populated from match details if needed
            )
            
            matches.append(match)
        
        logger.info(
            "Fetched recent matches",
            account_id=account_id,
            count=len(matches)
        )
        
        return matches
    
    async def get_match_details(self, match_id: int) -> dict:
        """Get full match details.
        
        Args:
            match_id: The match ID to fetch
            
        Returns:
            Full match details as dictionary
        """
        logger.info("Fetching match details", match_id=match_id)
        return await self._make_request(f"/matches/{match_id}")
    
    async def get_replay_url(self, match_id: int) -> Optional[str]:
        """Get the replay download URL for a match.
        
        Args:
            match_id: The match ID
            
        Returns:
            Replay URL if available, None otherwise
        """
        try:
            details = await self.get_match_details(match_id)
            
            # Check if replay URL is directly available
            if "replay_url" in details and details["replay_url"]:
                return details["replay_url"]
            
            # Construct URL from cluster and replay salt
            cluster = details.get("cluster")
            replay_salt = details.get("replay_salt")
            
            if cluster and replay_salt:
                url = f"http://replay{cluster}.valve.net/570/{match_id}_{replay_salt}.dem.bz2"
                return url
            
            logger.warning(
                "No replay information available",
                match_id=match_id
            )
            return None
        
        except OpenDotaError:
            logger.error("Failed to get replay URL", match_id=match_id)
            return None
