"""Main entry point for DotaForge."""

import asyncio
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.api.opendota import OpenDotaClient
from src.config import get_settings
from src.core.match_finder import MatchFinder
from src.core.replay_manager import ReplayManager
from src.core.storage_manager import StorageManager
from src.database import Database
from src.dota.camera import CameraController
from src.dota.launcher import DotaLauncher
from src.exceptions import DotaForgeError, RecordingError, DotaNotFoundError
from src.logger import logger
from src.recorder.ffmpeg import FFmpegConverter
from src.recorder.orchestrator import RecordingOrchestrator
from src.recorder.startmovie import StartMovieRecorder
from src.utils.dota_detector import find_dota2_installation


async def run_single():
    """Run a single recording cycle with full workflow."""
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("🎬 DOTAFORGE - Starting recording cycle")
    logger.info("=" * 60, player=settings.player_name)
    
    # Check dry run mode
    if settings.dry_run:
        logger.info("🧪 DRY RUN MODE - Will not launch Dota 2")
    
    # Initialize components
    db = Database()
    await db.init()
    
    client = OpenDotaClient()
    storage_mgr = StorageManager(settings.storage)
    
    try:
        # Check storage quota
        if not storage_mgr.check_storage_quota():
            logger.error("❌ Storage quota exceeded - stopping")
            return
        
        # Find next match
        finder = MatchFinder(client, db)
        match = await finder.find_next_match()
        
        if not match:
            logger.info("📭 No matches to record at this time")
            return
        
        logger.info(
            "🎯 Found match to record",
            match_id=match.match_id,
            hero=match.hero_name,
            kda=match.kda,
            result="Win" if match.is_win else "Loss",
            duration=match.duration_formatted
        )
        
        # Download replay
        replay_mgr = ReplayManager(client)
        
        try:
            replay_path = await replay_mgr.download_replay(match)
        except Exception as e:
            logger.error("Failed to download replay", error=str(e))
            await db.mark_processed(match, Path("none"), "failed", str(e))
            return
        
        # Check dry run mode
        if settings.dry_run:
            logger.info("🧪 Dry run - skipping actual recording")
            await db.mark_processed(match, Path("dry_run.mp4"), "skipped", "Dry run mode")
            
            # Clean up replay if configured
            if settings.storage.cleanup_replays:
                await replay_mgr.delete_replay(match.match_id)
                logger.info("🗑️  Deleted replay file (dry run)")
            
            return
        
        # Check if Dota 2 is available
        dota_path = settings.dota2_path or find_dota2_installation()
        
        if not dota_path:
            logger.error(
                "❌ Dota 2 not found. Please set DOTA2_PATH in your .env file."
            )
            await db.mark_processed(
                match, Path("none"), "failed", "Dota 2 not found"
            )
            return
        
        # Check if ffmpeg is available
        try:
            converter = FFmpegConverter()
        except Exception as e:
            logger.error(f"❌ FFmpeg not available: {e}")
            await db.mark_processed(
                match, Path("none"), "failed", f"FFmpeg error: {e}"
            )
            return
        
        # Initialize recording components
        logger.info("🎮 Initializing recording components...")
        
        launcher = DotaLauncher(dota_path)
        camera = CameraController()
        recorder = StartMovieRecorder()
        
        # Create orchestrator
        orchestrator = RecordingOrchestrator(
            launcher=launcher,
            camera=camera,
            recorder=recorder,
            converter=converter
        )
        
        # Run full recording workflow
        try:
            output_path = await orchestrator.record_match(match, replay_path)
            
            # Mark as successfully processed
            await db.mark_processed(match, output_path, "success")
            
            logger.info(
                "✅ Recording complete!",
                match_id=match.match_id,
                output=str(output_path)
            )
            
        except RecordingError as e:
            logger.error(f"❌ Recording failed: {e}")
            await db.mark_processed(match, Path("none"), "failed", str(e))
            return
        
        # Clean up replay if configured
        if settings.storage.cleanup_replays:
            await replay_mgr.delete_replay(match.match_id)
            logger.info("🗑️  Deleted replay file")
        
        # Clean up old videos
        deleted = await storage_mgr.cleanup_old_videos()
        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} old videos")
        
        logger.info("✅ Cycle complete!")
        
    except DotaNotFoundError as e:
        logger.error(f"❌ Dota 2 not found: {e}")
        logger.info("💡 Run 'python -m src.cli find-dota' to locate it")
        
    except Exception as e:
        logger.exception("Recording cycle failed", error=str(e))
        raise
    
    finally:
        await client.close()


def start_scheduler():
    """Start the scheduled recording service."""
    settings = get_settings()
    
    # Parse run time
    hour, minute = map(int, settings.run_time.split(":"))
    
    # Create scheduler
    scheduler = AsyncIOScheduler()
    
    # Add job
    scheduler.add_job(
        run_single,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=settings.timezone),
        id="dotaforge_daily",
        name="Daily Dota 2 Recording",
        replace_existing=True
    )
    
    logger.info("🚀 Scheduler started", 
                run_time=settings.run_time,
                timezone=settings.timezone)
    
    # Start scheduler
    scheduler.start()
    
    try:
        # Run forever
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏹️  Shutting down scheduler...")
        scheduler.shutdown()
    

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        asyncio.run(run_single())
    else:
        start_scheduler()
