"""Native Dota 2 recording using startmovie command."""

import asyncio
from pathlib import Path
from typing import Optional

from src.config import Settings, get_settings
from src.exceptions import RecordingError
from src.logger import logger


class StartMovieRecorder:
    """Records Dota 2 replays using the native startmovie command.
    
    This outputs TGA image sequences which must be converted to video
    using ffmpeg after recording.
    """
    
    def __init__(
        self,
        temp_dir: Path = None,
        settings: Optional[Settings] = None
    ):
        """Initialize the recorder.
        
        Args:
            temp_dir: Directory to store TGA frames
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self.temp_dir = temp_dir or Path("temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_recording = False
        self.current_match_id: Optional[int] = None
        self.start_time: Optional[float] = None
    
    def get_frame_pattern(self, match_id: int) -> str:
        """Get the file pattern for TGA frames.
        
        Args:
            match_id: Match ID
            
        Returns:
            Pattern string like "temp/12345678_"
        """
        return str(self.temp_dir / f"{match_id}_")
    
    def get_frame_glob(self, match_id: int) -> str:
        """Get glob pattern for finding frames.
        
        Args:
            match_id: Match ID
            
        Returns:
            Glob pattern like "temp/12345678_*.tga"
        """
        return str(self.temp_dir / f"{match_id}_*.tga")
    
    def generate_start_command(self, match_id: int) -> str:
        """Generate the console command to start recording.
        
        Args:
            match_id: Match ID for naming
            
        Returns:
            Console command string
        """
        pattern = self.get_frame_pattern(match_id)
        
        # startmovie outputs TGA format by default
        # Format: startmovie <basename> [raw|tga|jpg|wav]
        # We use tga for maximum quality (uncompressed)
        cmd = f'startmovie "{pattern}" tga'
        
        logger.info(
            "Generated startmovie command",
            match_id=match_id,
            pattern=pattern
        )
        
        return cmd
    
    def generate_stop_command(self) -> str:
        """Generate the console command to stop recording.
        
        Returns:
            Console command string
        """
        return "endmovie"
    
    async def start_recording(
        self,
        match_id: int,
        write_to_file: bool = True
    ) -> None:
        """Start recording by writing commands to file.
        
        Args:
            match_id: Match ID
            write_to_file: If True, write commands to autoexec file
        """
        if self.is_recording:
            raise RecordingError("Already recording")
        
        self.is_recording = True
        self.current_match_id = match_id
        self.start_time = asyncio.get_event_loop().time()
        
        if write_to_file:
            # Write command to file that will be executed by Dota 2
            cmd = self.generate_start_command(match_id)
            
            # Create a command file for execution
            cmd_file = Path("config/record_commands.cfg")
            cmd_file.write_text(
                f'echo "[DOTAFORGE] Starting recording for match {match_id}"\n'
                f"{cmd}\n",
                encoding="utf-8"
            )
            
            logger.info(
                "Recording commands written to file",
                file=str(cmd_file),
                match_id=match_id
            )
        
        logger.info("Recording started", match_id=match_id)
    
    async def stop_recording(self, write_to_file: bool = True) -> dict:
        """Stop recording.
        
        Args:
            write_to_file: If True, write stop command to file
            
        Returns:
            Recording statistics
        """
        if not self.is_recording:
            return {"frames": 0, "duration": 0}
        
        if write_to_file:
            cmd = self.generate_stop_command()
            
            # Append to command file
            cmd_file = Path("config/record_commands.cfg")
            current = cmd_file.read_text(encoding="utf-8") if cmd_file.exists() else ""
            cmd_file.write_text(
                current + f"\n{cmd}\n" +
                f'echo "[DOTAFORGE] Recording stopped"\n',
                encoding="utf-8"
            )
        
        # Wait a moment for frames to finish writing
        await asyncio.sleep(2)
        
        # Calculate stats
        end_time = asyncio.get_event_loop().time()
        duration = end_time - self.start_time if self.start_time else 0
        
        # Count frames
        frame_count = self.get_frame_count(self.current_match_id)
        
        self.is_recording = False
        
        stats = {
            "frames": frame_count,
            "duration": round(duration, 2),
            "fps": round(frame_count / duration, 2) if duration > 0 else 0
        }
        
        logger.info(
            "Recording stopped",
            match_id=self.current_match_id,
            frames=frame_count,
            duration=f"{duration:.2f}s",
            estimated_fps=stats["fps"]
        )
        
        self.current_match_id = None
        self.start_time = None
        
        return stats
    
    def get_frame_count(self, match_id: int) -> int:
        """Count recorded TGA frames.
        
        Args:
            match_id: Match ID
            
        Returns:
            Number of frames
        """
        import glob
        
        pattern = self.get_frame_glob(match_id)
        frames = glob.glob(pattern)
        return len(frames)
    
    def get_total_size_mb(self, match_id: int) -> float:
        """Get total size of TGA frames.
        
        Args:
            match_id: Match ID
            
        Returns:
            Size in MB
        """
        import glob
        
        pattern = self.get_frame_glob(match_id)
        frames = glob.glob(pattern)
        
        total_bytes = sum(Path(f).stat().st_size for f in frames)
        return total_bytes / (1024 * 1024)
    
    def get_first_frame(self, match_id: int) -> Optional[Path]:
        """Get path to first frame for pattern.
        
        Args:
            match_id: Match ID
            
        Returns:
            Path to first frame, or None if no frames
        """
        import glob
        
        pattern = self.get_frame_glob(match_id)
        frames = sorted(glob.glob(pattern))
        
        return Path(frames[0]) if frames else None
    
    def get_frame_pattern_for_ffmpeg(self, match_id: int) -> str:
        """Get frame pattern formatted for ffmpeg.
        
        Args:
            match_id: Match ID
            
        Returns:
            Pattern like "temp/12345678_%04d.tga"
        """
        return str(self.temp_dir / f"{match_id}_%04d.tga")
    
    def cleanup_frames(self, match_id: int) -> int:
        """Delete all TGA frames for a match.
        
        Args:
            match_id: Match ID
            
        Returns:
            Number of files deleted
        """
        import glob
        
        pattern = self.get_frame_glob(match_id)
        frames = glob.glob(pattern)
        
        deleted = 0
        for frame in frames:
            try:
                Path(frame).unlink()
                deleted += 1
            except OSError:
                pass
        
        if deleted > 0:
            logger.info(
                "Cleaned up TGA frames",
                match_id=match_id,
                deleted=deleted
            )
        
        return deleted
