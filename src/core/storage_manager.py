"""Storage management utilities."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import StorageConfig
from src.logger import logger


class StorageManager:
    """Manages disk space and automatic cleanup."""
    
    def __init__(self, config: StorageConfig):
        """Initialize storage manager.
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self.output_dir = Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def cleanup_old_videos(self, days: Optional[int] = None) -> int:
        """Delete videos older than specified days.
        
        Args:
            days: Delete videos older than this many days
            
        Returns:
            Number of videos deleted
        """
        days = days or self.config.auto_delete_days
        cutoff = datetime.now() - timedelta(days=days)
        
        deleted = 0
        freed_mb = 0
        
        for video in self.output_dir.glob("*.mp4"):
            # Get modification time
            mtime = datetime.fromtimestamp(video.stat().st_mtime)
            
            if mtime < cutoff:
                size_mb = video.stat().st_size / (1024 * 1024)
                video.unlink()
                deleted += 1
                freed_mb += size_mb
                
                logger.info(
                    "Deleted old video",
                    file=video.name,
                    age_days=(datetime.now() - mtime).days,
                    size_mb=round(size_mb, 2)
                )
        
        if deleted > 0:
            logger.info(
                "Video cleanup complete",
                deleted=deleted,
                freed_mb=round(freed_mb, 2)
            )
        
        return deleted
    
    def check_storage_quota(self) -> bool:
        """Check if storage is under quota.
        
        Returns:
            True if under quota, False if exceeded
        """
        total_size = sum(
            f.stat().st_size for f in self.output_dir.glob("*.mp4")
        ) / (1024**3)  # GB
        
        if total_size > self.config.max_storage_gb:
            logger.warning(
                "Storage quota exceeded",
                used_gb=round(total_size, 2),
                limit_gb=self.config.max_storage_gb
            )
            return False
        
        return True
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        videos = list(self.output_dir.glob("*.mp4"))
        
        total_size = sum(f.stat().st_size for f in videos)
        total_size_gb = total_size / (1024**3)
        
        oldest = None
        newest = None
        oldest_date = None
        newest_date = None
        
        oldest = None
        newest = None
        oldest_date = None
        newest_date = None
        
        if videos:
            oldest = min(videos, key=lambda f: f.stat().st_mtime)
            newest = max(videos, key=lambda f: f.stat().st_mtime)
            
            oldest_date = datetime.fromtimestamp(oldest.stat().st_mtime)
            newest_date = datetime.fromtimestamp(newest.stat().st_mtime)
        
        return {
            "video_count": len(videos),
            "total_size_gb": round(total_size_gb, 2),
            "total_size_bytes": total_size,
            "oldest_video": oldest.name if oldest else None,
            "oldest_video_date": oldest_date.isoformat() if oldest_date else None,
            "newest_video": newest.name if newest else None,
            "newest_video_date": newest_date.isoformat() if newest_date else None,
            "available_gb": round(self.config.max_storage_gb - total_size_gb, 2),
            "quota_percent": round((total_size_gb / self.config.max_storage_gb) * 100, 1)
        }
    
    def get_temp_size(self) -> float:
        """Get size of temp directory in GB.
        
        Returns:
            Size in GB
        """
        temp_dir = Path("temp")
        if not temp_dir.exists():
            return 0
        
        total_size = sum(
            f.stat().st_size for f in temp_dir.rglob("*") if f.is_file()
        ) / (1024**3)
        
        return round(total_size, 2)
    
    def cleanup_temp(self) -> int:
        """Clean up all temporary files.
        
        Returns:
            Number of files deleted
        """
        temp_dir = Path("temp")
        if not temp_dir.exists():
            return 0
        
        deleted = 0
        for file in temp_dir.rglob("*"):
            if file.is_file():
                file.unlink()
                deleted += 1
        
        if deleted > 0:
            logger.info("Cleaned up temp files", deleted=deleted)
        
        return deleted
