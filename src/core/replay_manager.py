"""Replay download and management."""

import bz2
from pathlib import Path
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm.asyncio import tqdm

from src.api.opendota import OpenDotaClient
from src.config import Settings, get_settings
from src.exceptions import ReplayDownloadError, ReplayCorruptedError
from src.logger import logger
from src.models.match import Match


class ReplayManager:
    """Manages Dota 2 replay file downloads."""
    
    def __init__(
        self,
        client: Optional[OpenDotaClient] = None,
        replays_dir: Optional[Path] = None,
        settings: Optional[Settings] = None
    ):
        """Initialize the replay manager.
        
        Args:
            client: OpenDota client (creates new if not provided)
            replays_dir: Directory to store replay files
            settings: Application settings
        """
        self.client = client or OpenDotaClient()
        self.replays_dir = replays_dir or Path("replays")
        self.replays_dir.mkdir(parents=True, exist_ok=True)
    
    def get_replay_path(self, match_id: int) -> Path:
        """Get the local file path for a replay.
        
        Args:
            match_id: The match ID
            
        Returns:
            Path to the .dem file
        """
        return self.replays_dir / f"{match_id}.dem"
    
    async def is_downloaded(self, match_id: int) -> bool:
        """Check if a replay is already downloaded and valid.
        
        Args:
            match_id: The match ID to check
            
        Returns:
            True if replay exists and is valid
        """
        replay_path = self.get_replay_path(match_id)
        
        if not replay_path.exists():
            return False
        
        # Check file size (must be > 1MB to be valid)
        file_size = replay_path.stat().st_size
        if file_size < 1024 * 1024:
            logger.warning(
                "Existing replay file too small, will re-download",
                match_id=match_id,
                size_bytes=file_size
            )
            return False
        
        return True
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def download_replay(
        self,
        match: Match,
        progress: bool = True
    ) -> Path:
        """Download a replay from Valve CDN.
        
        Downloads the .dem.bz2 file, decompresses it, and verifies integrity.
        
        Args:
            match: Match object with replay_url
            progress: Show download progress bar
            
        Returns:
            Path to downloaded .dem file
            
        Raises:
            ReplayDownloadError: If download fails
            ReplayCorruptedError: If file is invalid
        """
        # Check if already downloaded
        replay_path = self.get_replay_path(match.match_id)
        if await self.is_downloaded(match.match_id):
            logger.info(
                "Replay already downloaded",
                match_id=match.match_id,
                path=str(replay_path)
            )
            return replay_path
        
        # Get replay URL
        if match.replay_url:
            replay_url = match.replay_url
        else:
            replay_url = await self.client.get_replay_url(match.match_id)
        
        if not replay_url:
            raise ReplayDownloadError(
                f"No replay URL available for match {match.match_id}"
            )
        
        logger.info(
            "Downloading replay",
            match_id=match.match_id,
            url=replay_url[:60] + "..."
        )
        
        # Temporary .bz2 file
        temp_bz2 = replay_path.with_suffix(".dem.bz2")
        
        try:
            # Download with streaming and progress
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", replay_url) as response:
                    response.raise_for_status()
                    
                    # Get content length for progress bar
                    total = int(response.headers.get("content-length", 0))
                    
                    # Write to file
                    with open(temp_bz2, "wb") as f:
                        if progress and total > 0:
                            # Use tqdm for progress bar
                            with tqdm(
                                total=total,
                                unit="B",
                                unit_scale=True,
                                desc=f"Match {match.match_id}"
                            ) as pbar:
                                async for chunk in response.aiter_bytes(chunk_size=8192):
                                    f.write(chunk)
                                    pbar.update(len(chunk))
                        else:
                            # No progress bar
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)
            
            # Decompress bz2
            logger.info("Decompressing replay", match_id=match.match_id)
            
            with bz2.BZ2File(temp_bz2, "rb") as src, open(replay_path, "wb") as dst:
                # Read and write in chunks to handle large files
                while True:
                    chunk = src.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    dst.write(chunk)
            
            # Clean up .bz2 file
            temp_bz2.unlink()
            
            # Verify integrity
            file_size = replay_path.stat().st_size
            if file_size < 1024 * 1024:  # Less than 1MB is suspicious
                replay_path.unlink()
                raise ReplayCorruptedError(
                    f"Replay file too small: {file_size} bytes"
                )
            
            logger.info(
                "Replay downloaded successfully",
                match_id=match.match_id,
                size_mb=round(file_size / (1024 * 1024), 2),
                path=str(replay_path)
            )
            
            return replay_path
        
        except httpx.HTTPError as e:
            logger.error(
                "HTTP error downloading replay",
                match_id=match.match_id,
                error=str(e)
            )
            raise ReplayDownloadError(f"HTTP error: {e}") from e
        
        except Exception as e:
            # Clean up partial files
            if temp_bz2.exists():
                temp_bz2.unlink()
            if replay_path.exists():
                replay_path.unlink()
            
            logger.error(
                "Failed to download replay",
                match_id=match.match_id,
                error=str(e)
            )
            raise ReplayDownloadError(f"Download failed: {e}") from e
    
    async def delete_replay(self, match_id: int) -> bool:
        """Delete a downloaded replay.
        
        Args:
            match_id: The match ID to delete
            
        Returns:
            True if file was deleted, False if it didn't exist
        """
        replay_path = self.get_replay_path(match_id)
        
        if replay_path.exists():
            replay_path.unlink()
            logger.info("Deleted replay file", match_id=match_id)
            return True
        
        return False
    
    async def cleanup_all(self) -> int:
        """Delete all replay files.
        
        Returns:
            Number of files deleted
        """
        count = 0
        for replay_file in self.replays_dir.glob("*.dem"):
            replay_file.unlink()
            count += 1
        
        logger.info(f"Cleaned up {count} replay files")
        return count
