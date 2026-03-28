"""FFmpeg video conversion utilities."""

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from src.config import Settings, get_settings
from src.exceptions import FFmpegError
from src.logger import logger


class FFmpegConverter:
    """Converts TGA frames to MP4 video using ffmpeg."""
    
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        settings: Optional[Settings] = None
    ):
        """Initialize the converter.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable
            settings: Application settings
        """
        self.ffmpeg_path = ffmpeg_path
        self.settings = settings or get_settings()
        
        # Verify ffmpeg is available
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self) -> bool:
        """Verify ffmpeg is installed and accessible.
        
        Returns:
            True if ffmpeg is available
            
        Raises:
            FFmpegError: If ffmpeg is not found
        """
        ffmpeg_exe = shutil.which(self.ffmpeg_path)
        
        if not ffmpeg_exe:
            raise FFmpegError(
                f"ffmpeg not found: {self.ffmpeg_path}\n"
                "Please install ffmpeg and ensure it's in your PATH.\n"
                "Download from: https://ffmpeg.org/download.html"
            )
        
        # Update path to full executable
        self.ffmpeg_path = ffmpeg_exe
        
        return True
    
    async def convert_to_mp4(
        self,
        frame_pattern: str,
        output_path: Path,
        fps: Optional[int] = None,
        crf: Optional[int] = None,
        audio_file: Optional[Path] = None
    ) -> Path:
        """Convert TGA frame sequence to MP4.
        
        Args:
            frame_pattern: Path pattern for frames (e.g., "temp/12345_%04d.tga")
            output_path: Output video file path
            fps: Frames per second (uses config if not set)
            crf: Quality setting (uses config if not set)
            audio_file: Optional audio file to include
            
        Returns:
            Path to output video file
            
        Raises:
            FFmpegError: If conversion fails
        """
        fps = fps or self.settings.recording.framerate
        crf = crf or self.settings.recording.crf
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Starting video conversion",
            frame_pattern=frame_pattern,
            output=str(output_path),
            fps=fps,
            crf=crf
        )
        
        # Build ffmpeg command
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite output
            "-framerate", str(fps),
            "-i", frame_pattern,
        ]
        
        # Add audio if provided
        if audio_file and audio_file.exists():
            cmd.extend([
                "-i", str(audio_file),
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",  # Match shortest input duration
            ])
            logger.info("Including audio track", audio_file=str(audio_file))
        
        # Video codec settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",  # For compatibility
            "-movflags", "+faststart",  # Web optimization
        ])
        
        # Output file
        cmd.append(str(output_path))
        
        # Run ffmpeg
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise FFmpegError(
                    f"FFmpeg failed with code {process.returncode}: {error_msg[:500]}"
                )
            
            # Verify output
            if not output_path.exists():
                raise FFmpegError("Output file was not created")
            
            file_size = output_path.stat().st_size
            
            logger.info(
                "Video conversion complete",
                output=str(output_path),
                size_mb=round(file_size / (1024 * 1024), 2)
            )
            
            return output_path
            
        except asyncio.CancelledError:
            # Clean up partial output
            if output_path.exists():
                output_path.unlink()
            raise
        
        except Exception as e:
            # Clean up partial output
            if output_path.exists():
                output_path.unlink()
            raise FFmpegError(f"Conversion failed: {e}") from e
    
    async def get_video_info(self, video_path: Path) -> dict:
        """Get video file information using ffprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video info (duration, resolution, etc.)
        """
        ffprobe_path = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
        
        if not shutil.which(ffprobe_path):
            logger.warning("ffprobe not found, cannot get video info")
            return {}
        
        cmd = [
            ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration,size",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-of", "json",
            str(video_path)
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {}
            
            import json
            info = json.loads(stdout.decode())
            
            return {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size_bytes": int(info.get("format", {}).get("size", 0)),
                "width": int(info.get("streams", [{}])[0].get("width", 0)),
                "height": int(info.get("streams", [{}])[0].get("height", 0)),
            }
            
        except Exception as e:
            logger.warning("Failed to get video info", error=str(e))
            return {}
    
    def is_available(self) -> bool:
        """Check if ffmpeg is available.
        
        Returns:
            True if ffmpeg can be used
        """
        return shutil.which(self.ffmpeg_path) is not None
