"""Match finder with filtering capabilities."""

from datetime import datetime, timedelta
from typing import Optional, List

from src.api.opendota import OpenDotaClient
from src.config import Settings, get_settings
from src.database import Database
from src.logger import logger
from src.models.match import Match


class MatchFinder:
    """Finds and filters matches for recording based on user criteria."""
    
    def __init__(
        self,
        client: OpenDotaClient,
        db: Database,
        settings: Optional[Settings] = None
    ):
        """Initialize the match finder.
        
        Args:
            client: OpenDota API client
            db: Database for tracking processed matches
            settings: Application settings (uses global if not provided)
        """
        self.client = client
        self.db = db
        self.config = (settings or get_settings()).match_selection
        self.account_id = (settings or get_settings()).steam_account_id
    
    async def find_next_match(self) -> Optional[Match]:
        """Find the next match to record based on criteria.
        
        Algorithm:
        1. Fetch recent matches from OpenDota
        2. Filter by date (last 24 hours)
        3. Apply user filters (wins, hero, duration, KDA)
        4. Sort by configured method
        5. Return first unprocessed match
        
        Returns:
            Match object if found, None otherwise
        """
        logger.info(
            "Searching for next match to record",
            account_id=self.account_id,
            filters={
                "only_wins": self.config.only_wins,
                "hero_filter": self.config.hero_filter,
                "min_duration": self.config.min_duration_seconds,
                "max_duration": self.config.max_duration_seconds,
                "min_kda": self.config.min_kda,
                "sort_by": self.config.sort_by
            }
        )
        
        # Fetch recent matches
        matches = await self.client.get_recent_matches(self.account_id)
        
        if not matches:
            logger.info("No matches found in recent history")
            return None
        
        # Filter by date (last 24 hours)
        cutoff = datetime.now() - timedelta(days=1)
        recent_matches = [m for m in matches if m.start_time > cutoff]
        
        if not recent_matches:
            logger.info(
                "No matches from last 24 hours",
                total_matches=len(matches),
                oldest_match=matches[-1].start_time.isoformat() if matches else None
            )
            return None
        
        logger.info(
            "Found recent matches",
            count=len(recent_matches),
            total_scanned=len(matches)
        )
        
        # Apply filters
        eligible = self._apply_filters(recent_matches)
        
        if not eligible:
            logger.info(
                "No matches meet filter criteria",
                recent_count=len(recent_matches),
                filters_applied=True
            )
            return None
        
        logger.info(
            "Matches passing filters",
            count=len(eligible)
        )
        
        # Sort
        eligible = self._sort_matches(eligible)
        
        # Find first unprocessed
        for match in eligible:
            is_processed = await self.db.is_processed(match.match_id)
            
            if not is_processed:
                logger.info(
                    "Found eligible unprocessed match",
                    match_id=match.match_id,
                    hero=match.hero_name,
                    kda=match.kda,
                    win=match.is_win,
                    duration=match.duration_formatted,
                    start_time=match.start_time.isoformat()
                )
                return match
            else:
                logger.debug(
                    "Match already processed, skipping",
                    match_id=match.match_id
                )
        
        logger.info(
            "All eligible matches already processed",
            eligible_count=len(eligible)
        )
        return None
    
    def _apply_filters(self, matches: List[Match]) -> List[Match]:
        """Apply user-defined filters to match list.
        
        Args:
            matches: List of matches to filter
            
        Returns:
            Filtered list of matches
        """
        result = matches
        
        # Win/Loss filter
        if self.config.only_wins:
            result = [m for m in result if m.is_win]
            logger.debug(f"Win filter: {len(result)} matches remaining")
        elif self.config.only_losses:
            result = [m for m in result if not m.is_win]
            logger.debug(f"Loss filter: {len(result)} matches remaining")
        
        # Duration filter
        result = [
            m for m in result
            if self.config.min_duration_seconds <= m.duration_seconds <= self.config.max_duration_seconds
        ]
        logger.debug(f"Duration filter: {len(result)} matches remaining")
        
        # KDA filter
        result = [m for m in result if m.kda >= self.config.min_kda]
        logger.debug(f"KDA filter: {len(result)} matches remaining")
        
        # Hero filter (case-insensitive)
        if self.config.hero_filter:
            hero_name = self.config.hero_filter.lower()
            result = [
                m for m in result
                if m.hero_name and m.hero_name.lower() == hero_name
            ]
            logger.debug(f"Hero filter '{hero_name}': {len(result)} matches remaining")
        
        return result
    
    def _sort_matches(self, matches: List[Match]) -> List[Match]:
        """Sort matches by configured criteria.
        
        Args:
            matches: List of matches to sort
            
        Returns:
            Sorted list of matches
        """
        if self.config.sort_by == "date":
            # Most recent first
            return sorted(matches, key=lambda m: m.start_time, reverse=True)
        
        elif self.config.sort_by == "kda":
            # Highest KDA first
            return sorted(matches, key=lambda m: m.kda, reverse=True)
        
        elif self.config.sort_by == "duration":
            # Longest matches first
            return sorted(matches, key=lambda m: m.duration_seconds, reverse=True)
        
        return matches
    
    async def find_matches(
        self,
        count: int = 1,
        days_back: int = 1
    ) -> List[Match]:
        """Find multiple matches for recording.
        
        Args:
            count: Maximum number of matches to find
            days_back: Look for matches from last N days
            
        Returns:
            List of unprocessed matches
        """
        matches = []
        cutoff = datetime.now() - timedelta(days=days_back)
        
        # Fetch recent matches (this gets last 20 by default from OpenDota)
        recent = await self.client.get_recent_matches(self.account_id)
        
        # Filter by date
        recent = [m for m in recent if m.start_time > cutoff]
        
        # Apply filters
        eligible = self._apply_filters(recent)
        eligible = self._sort_matches(eligible)
        
        # Find unprocessed
        for match in eligible:
            if len(matches) >= count:
                break
            
            if not await self.db.is_processed(match.match_id):
                matches.append(match)
        
        logger.info(
            f"Found {len(matches)} matches for recording",
            requested=count,
            found=len(matches)
        )
        
        return matches
