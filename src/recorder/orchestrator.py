"""Main recording orchestrator that coordinates the full workflow."""

import asyncio
from pathlib import Path
from typing import Optional

from src.config import Settings, get_settings
from src.dota.camera import CameraController
from src.dota.launcher import DotaLauncher
from src.exceptions import RecordingError
from src.logger import logger
from src.models.match import Match
from src.recorder.ffmpeg import FFmpegConverter
from src.recorder.startmovie import StartMovieRecorder


class RecordingOrchestrator:
    """Coordinates the entire recording workflow from launch to final video."""
    
    def __init__(
        self,
        launcher: DotaLauncher,
        camera: CameraController,
        recorder: StartMovieRecorder,
        converter: FFmpegConverter,
        output_dir: Path = None,
        settings: Optional[Settings] = None
    ):
        """Initialize the orchestrator.
        
        Args:
            launcher: Dota 2 launcher
            camera: Camera controller
            recorder: StartMovie recorder
            converter: FFmpeg converter
            output_dir: Directory for output videos
            settings: Application settings
        """
        self.launcher = launcher
        self.camera = camera
        self.recorder = recorder
        self.converter = converter
        self.settings = settings or get_settings()
        
        self.output_dir = output_dir or Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def record_match(self, match: Match, replay_path: Path) -> Path:
        """Record a complete match from start to finish.
        
        This method orchestrates the entire recording workflow:
        1. Launch Dota 2 with the replay
        2. Wait for game to load
        3. Set up camera for player perspective
        4. Wait for hero to spawn
        5. Start TGA recording
        6. Wait for match to complete
        7. Stop recording
        8. Convert TGA frames to MP4
        9. Clean up temporary files
        
        Args:
            match: Match object with metadata
            replay_path: Path to the .dem replay file
            
        Returns:
            Path to the final MP4 video file
            
        Raises:
            RecordingError: If any step fails
        """
        output_path = self.output_dir / f"{match.match_id}.mp4"
        
        logger.info(
            "=" * 60
        )
        logger.info(
            "🎬 Starting full recording workflow",
            match_id=match.match_id,
            hero=match.hero_name,
            duration=match.duration_formatted
        )
        logger.info(
            "=" * 60
        )
        
        try:
            # Phase 1: Launch
            logger.info("Phase 1/5: Launching Dota 2")
            await self.launcher.launch_with_replay(
                replay_path,
                match.player_slot
            )
            
            # Phase 2: Wait for load
            logger.info("Phase 2/5: Waiting for game to load")
            if not await self.launcher.wait_for_load():
                raise RecordingError("Dota 2 failed to load properly")
            
            # Phase 3: Camera setup (handled by autoexec)
            logger.info("Phase 3/5: Camera setup (autoexec)")
            await self.camera.wait_for_hero_spawn()
            
            # Write recording start command
            await self.recorder.start_recording(match.match_id)
            
            # Phase 4: Record the match
            logger.info("Phase 4/5: Recording match")
            
            # Wait for the match duration + buffer
            await self.camera.detect_match_end(
                match.duration_seconds,
                timeout_buffer=60
            )
            
            # Stop recording
            await self.recorder.stop_recording()
            
            # Phase 5: Convert to MP4
            logger.info("Phase 5/5: Converting to MP4")
            
            # Ensure Dota 2 is closed before conversion
            await self.launcher.terminate()
            
            frame_pattern = self.recorder.get_frame_pattern_for_ffmpeg(match.match_id)
            
            await self.converter.convert_to_mp4(
                frame_pattern=frame_pattern,
                output_path=output_path,
                fps=self.settings.recording.framerate,
                crf=self.settings.recording.crf
            )
            
            # Cleanup
            if self.settings.storage.cleanup_temp:
                deleted = self.recorder.cleanup_frames(match.match_id)
                logger.info(
                    "Cleaned up temporary files",
                    frames_deleted=deleted
                )
            
            logger.info(
                "=" * 60
            )
            logger.info(
                "✅ Recording workflow complete!",
                match_id=match.match_id,
                output=str(output_path)
            )
            logger.info(
                "=" * 60
            )
            
            return output_path
            
        except Exception as e:
            logger.exception(
                "Recording workflow failed",
                match_id=match.match_id,
                error=str(e)
            )
            
            # Cleanup
            try:
                await self.launcher.terminate(force=True)
                if self.settings.storage.cleanup_temp:
                    self.recorder.cleanup_frames(match.match_id)
            except Exception as cleanup_error:
                logger.warning(
                    "Cleanup failed after error",
                    error=str(cleanup_error)
                )
            
            raise RecordingError(f"Recording failed: {e}") from e
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        try:
            await self.launcher.terminate()
        except Exception as e:
            logger.warning("Error during cleanup", error=str(e))
