"""Database operations for tracking processed matches."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiosqlite

from src.models.match import Match, ProcessedMatch


class Database:
    """SQLite database for tracking processed matches."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/processed.db
        """
        self.db_path = db_path or Path("data/processed.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    async def init(self) -> None:
        """Initialize database tables if they don't exist."""
        if self._initialized:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS processed_matches (
                    match_id INTEGER PRIMARY KEY,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    video_path TEXT,
                    status TEXT CHECK(status IN ('success', 'failed', 'skipped')),
                    error_message TEXT,
                    hero_name TEXT,
                    kda REAL,
                    is_win BOOLEAN,
                    duration_seconds INTEGER
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_recorded_at 
                ON processed_matches(recorded_at)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON processed_matches(status)
            """)
            
            await db.commit()
        
        self._initialized = True
    
    async def is_processed(self, match_id: int) -> bool:
        """Check if a match has already been processed.
        
        Args:
            match_id: The match ID to check
            
        Returns:
            True if the match has been processed, False otherwise
        """
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM processed_matches WHERE match_id = ?",
                (match_id,)
            ) as cursor:
                return await cursor.fetchone() is not None
    
    async def mark_processed(
        self,
        match: Match,
        video_path: Path,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Mark a match as processed in the database.
        
        Args:
            match: The match that was processed
            video_path: Path to the output video file
            status: One of 'success', 'failed', or 'skipped'
            error_message: Optional error message if status is 'failed'
        """
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO processed_matches 
                (match_id, video_path, status, error_message, hero_name, kda, is_win, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match.match_id,
                str(video_path),
                status,
                error_message,
                match.hero_name,
                match.kda,
                match.is_win,
                match.duration_seconds
            ))
            await db.commit()
    
    async def get_recent_matches(
        self,
        days: int = 10,
        status: Optional[str] = None
    ) -> List[ProcessedMatch]:
        """Get recently processed matches.
        
        Args:
            days: Number of days to look back
            status: Optional filter by status
            
        Returns:
            List of processed match records
        """
        await self.init()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT match_id, recorded_at, video_path, status, 
                   error_message, hero_name, kda, is_win
            FROM processed_matches 
            WHERE recorded_at >= ?
        """
        params = [cutoff.isoformat()]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY recorded_at DESC"
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    ProcessedMatch(
                        match_id=row["match_id"],
                        recorded_at=datetime.fromisoformat(row["recorded_at"]),
                        video_path=Path(row["video_path"]),
                        status=row["status"],
                        error_message=row["error_message"],
                        hero_name=row["hero_name"],
                        kda=row["kda"],
                        is_win=bool(row["is_win"])
                    )
                    for row in rows
                ]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get recording statistics.
        
        Returns:
            Dictionary with statistics including total recorded, failed, etc.
        """
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Total counts by status
            async with db.execute("""
                SELECT status, COUNT(*) as count 
                FROM processed_matches 
                GROUP BY status
            """) as cursor:
                rows = await cursor.fetchall()
                for status, count in rows:
                    stats[f"total_{status}"] = count
            
            # Last recorded match
            async with db.execute("""
                SELECT match_id, recorded_at, hero_name
                FROM processed_matches 
                WHERE status = 'success'
                ORDER BY recorded_at DESC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                if row:
                    stats["last_recorded"] = {
                        "match_id": row[0],
                        "recorded_at": row[1],
                        "hero": row[2]
                    }
            
            # Average KDA
            async with db.execute("""
                SELECT AVG(kda) as avg_kda
                FROM processed_matches 
                WHERE status = 'success'
            """) as cursor:
                row = await cursor.fetchone()
                stats["average_kda"] = round(row[0], 2) if row[0] else 0
            
            return stats
    
    async def delete_old_records(self, days: int = 30) -> int:
        """Delete records older than specified days.
        
        Args:
            days: Delete records older than this many days
            
        Returns:
            Number of records deleted
        """
        await self.init()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "DELETE FROM processed_matches WHERE recorded_at < ?",
                (cutoff.isoformat(),)
            ) as cursor:
                count = cursor.rowcount
                await db.commit()
                return count
