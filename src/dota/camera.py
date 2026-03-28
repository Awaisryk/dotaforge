"""Camera control for spectator mode."""

import asyncio
from pathlib import Path
from typing import Optional

from src.config import Settings, get_settings
from src.exceptions import CameraError
from src.logger import logger


class CameraController:
    """Controls Dota 2 spectator camera for recording."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize camera controller.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
    
    def generate_commands(self, player_slot: int, match_id: int) -> str:
        """Generate console commands to set up camera.
        
        Args:
            player_slot: Player slot to spectate
            match_id: Match ID for naming
            
        Returns:
            Console commands as string
        """
        # Build command sequence
        commands = [
            "// Camera setup commands",
            f'echo "[DOTAFORGE] Setting up camera for player slot {player_slot}"',
            "",
            "// Ensure spectator mode",
            "dota_spectator_mode 1",
            "dota_set_spectator_statue_mode 0",
            "spec_mode 4",
            "",
            "// Switch to player",
            f"spec_player {player_slot}",
            "",
            "// Camera settings",
            "dota_camera_disable_zoom 1",
            "dota_camera_edgemove 0",
            f'dota_camera_speed {self.settings.recording.framerate * 50}',
            "",
            "// Wait for game to start",
            'echo "[DOTAFORGE] Camera setup complete"',
        ]
        
        return "\n".join(commands)
    
    def write_command_file(self, player_slot: int, match_id: int) -> Path:
        """Write camera setup commands to file.
        
        Args:
            player_slot: Player slot to spectate
            match_id: Match ID for naming
            
        Returns:
            Path to command file
        """
        commands = self.generate_commands(player_slot, match_id)
        
        cmd_file = Path("config/camera_commands.cfg")
        cmd_file.write_text(commands, encoding="utf-8")
        
        logger.debug(
            "Wrote camera commands to file",
            file=str(cmd_file),
            player_slot=player_slot
        )
        
        return cmd_file
    
    async def wait_for_hero_spawn(self, timeout: int = 120) -> bool:
        """Wait until the hero has spawned in-game.
        
        In Dota 2 replays, this is typically at game time 0:00.
        We'll wait for the replay time to advance.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if hero spawned, False if timeout
        """
        logger.info("Waiting for hero spawn in replay")
        
        # In a full implementation, this would check the game time via console
        # For now, wait a fixed amount of time after game load
        # Real games start around 0:00 after the strategy phase
        
        await asyncio.sleep(10)  # Wait for strategy phase + start
        
        logger.info("Hero should now be spawned")
        return True
    
    def set_recording_start_point(self, match_id: int) -> str:
        """Generate command to start recording.
        
        Args:
            match_id: Match ID for naming
            
        Returns:
            Console command
        """
        # Use startmovie to begin recording
        # TGA format outputs frames as individual images
        temp_dir = Path("temp").resolve()
        frame_pattern = temp_dir / f"{match_id}_"
        
        cmd = f'startmovie "{frame_pattern}" tga'
        
        logger.info(
            "Recording start command",
            match_id=match_id,
            pattern=str(frame_pattern)
        )
        
        return cmd
    
    def set_recording_stop_point(self) -> str:
        """Generate command to stop recording.
        
        Returns:
            Console command
        """
        return "endmovie"
    
    async def detect_match_end(self, duration_seconds: int, timeout_buffer: int = 60) -> bool:
        """Detect when the match has ended in the replay.
        
        Args:
            duration_seconds: Expected match duration
            timeout_buffer: Extra time to wait after duration
            
        Returns:
            True when match appears to have ended
        """
        total_wait = duration_seconds + timeout_buffer
        
        logger.info(
            "Waiting for match to end",
            duration=duration_seconds,
            buffer=timeout_buffer,
            total_wait=total_wait
        )
        
        await asyncio.sleep(total_wait)
        
        logger.info("Match should be complete")
        return True
