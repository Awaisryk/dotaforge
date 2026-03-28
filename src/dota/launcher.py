"""Dota 2 process launcher and management."""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List

import psutil

from src.config import Settings, get_settings
from src.exceptions import DotaLaunchError, DotaNotFoundError
from src.logger import logger
from src.utils.dota_detector import find_dota2_installation, get_dota2_exe_path


class DotaLauncher:
    """Manages Dota 2 process lifecycle for replay recording."""
    
    def __init__(self, dota2_path: Optional[Path] = None, settings: Optional[Settings] = None):
        """Initialize the Dota 2 launcher.
        
        Args:
            dota2_path: Path to Dota 2 installation (auto-detected if not provided)
            settings: Application settings
        """
        self.settings = settings or get_settings()
        
        # Get Dota 2 path
        if dota2_path:
            self.dota2_path = dota2_path
        elif self.settings.dota2_path:
            self.dota2_path = self.settings.dota2_path
        else:
            self.dota2_path = find_dota2_installation()
        
        if not self.dota2_path:
            raise DotaNotFoundError(
                "Could not find Dota 2 installation. "
                "Please set DOTA2_PATH in your .env file."
            )
        
        self.exe_path = get_dota2_exe_path(self.dota2_path)
        
        if not self.exe_path.exists():
            raise DotaNotFoundError(f"Dota 2 executable not found: {self.exe_path}")
        
        self.process: Optional[subprocess.Popen] = None
        self._monitor_task: Optional[asyncio.Task] = None
    
    def _build_launch_command(
        self,
        replay_path: Path,
        player_slot: int,
        width: int = 1920,
        height: int = 1080
    ) -> list:
        """Build the Dota 2 launch command.
        
        Args:
            replay_path: Path to the .dem replay file
            player_slot: Player slot to spectate
            width: Window width
            height: Window height
            
        Returns:
            List of command arguments
        """
        # Get absolute paths
        replay_abs = replay_path.resolve()
        
        # Build command
        cmd = [
            str(self.exe_path),
            "-console",           # Enable console
            "-novid",             # Skip intro video
            "-high",              # High process priority
            "-windowed",          # Windowed mode (easier to manage)
            "-noborder",          # Borderless window
            "-width", str(width),
            "-height", str(height),
            "+con_enable", "1",   # Ensure console is enabled
            "+playdemo", str(replay_abs),
            "+exec", "config/record_auto.cfg",  # Load autoexec
        ]
        
        return cmd
    
    async def launch_with_replay(
        self,
        replay_path: Path,
        player_slot: int,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> None:
        """Launch Dota 2 with a replay loaded.
        
        Args:
            replay_path: Path to the .dem replay file
            player_slot: Player slot to spectate
            width: Window width (uses config if not specified)
            height: Window height (uses config if not specified)
            
        Raises:
            DotaLaunchError: If Dota 2 fails to launch
        """
        # Parse resolution from settings
        if width is None or height is None:
            res = self.settings.recording.resolution
            try:
                w, h = map(int, res.split("x"))
                width = width or w
                height = height or h
            except ValueError:
                width = width or 1920
                height = height or 1080
        
        cmd = self._build_launch_command(replay_path, player_slot, width, height)
        
        logger.info(
            "Launching Dota 2",
            replay=str(replay_path),
            player_slot=player_slot,
            resolution=f"{width}x{height}"
        )
        
        # Kill any existing Dota 2 processes
        await self._kill_existing_dota()
        
        try:
            # Launch Dota 2
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                # Don't create a new console window on Windows
                creationflags=0x08000000  # CREATE_NO_WINDOW constant
            )
            
            # Wait a moment for process to start
            await asyncio.sleep(3)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise DotaLaunchError(
                    f"Dota 2 exited immediately with code {self.process.poll()}. "
                    f"STDERR: {stderr[:500]}"
                )
            
            logger.info(
                "Dota 2 launched successfully",
                pid=self.process.pid
            )
            
            # Start monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_process())
            
        except Exception as e:
            logger.error("Failed to launch Dota 2", error=str(e))
            raise DotaLaunchError(f"Launch failed: {e}") from e
    
    async def _kill_existing_dota(self) -> int:
        """Kill any existing Dota 2 processes.
        
        Returns:
            Number of processes killed
        """
        killed = 0
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Check if it's a Dota 2 process
                if proc.info['name'].lower() in ['dota2.exe', 'dota2']:
                    logger.warning(
                        "Killing existing Dota 2 process",
                        pid=proc.info['pid']
                    )
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if killed > 0:
            # Wait a moment for processes to terminate
            await asyncio.sleep(2)
        
        return killed
    
    async def _monitor_process(self):
        """Background task to monitor Dota 2 process."""
        if not self.process:
            return
        
        try:
            while self.is_running():
                await asyncio.sleep(5)
            
            # Process ended
            logger.info("Dota 2 process ended")
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error monitoring Dota 2 process", error=str(e))
    
    def is_running(self) -> bool:
        """Check if Dota 2 process is still running.
        
        Returns:
            True if running, False otherwise
        """
        if self.process is None:
            return False
        
        return self.process.poll() is None
    
    async def wait_for_load(self, timeout: Optional[int] = None) -> bool:
        """Wait for Dota 2 to finish loading.
        
        This checks various indicators that the game has loaded:
        - Process is still running
        - Window is visible (if possible to detect)
        - Console is responsive (Phase 3)
        
        Args:
            timeout: Maximum time to wait in seconds (uses config if not set)
            
        Returns:
            True if loaded successfully, False if timeout or error
        """
        timeout = timeout or self.settings.dota_load_timeout
        
        logger.info(f"Waiting for Dota 2 to load (timeout: {timeout}s)")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed > timeout:
                logger.error(f"Timeout waiting for Dota 2 to load ({timeout}s)")
                return False
            
            if not self.is_running():
                logger.error("Dota 2 process ended while waiting for load")
                return False
            
            # TODO: Check for actual game loaded state
            # This would involve reading console logs or checking window state
            # For now, just wait a reasonable amount of time
            
            await asyncio.sleep(1)
            
            # After 15 seconds, assume it's loaded
            if elapsed > 15:
                logger.info("Dota 2 appears to be loaded (15s elapsed)")
                return True
    
    async def terminate(self, force: bool = False) -> None:
        """Terminate the Dota 2 process.
        
        Args:
            force: If True, force kill immediately. If False, try graceful shutdown first.
        """
        if not self.process:
            return
        
        if not self.is_running():
            logger.debug("Dota 2 process already terminated")
            return
        
        logger.info("Terminating Dota 2 process", force=force)
        
        try:
            if not force:
                # Try graceful termination first
                self.process.terminate()
                
                # Wait up to 10 seconds
                try:
                    self.process.wait(timeout=10)
                    logger.info("Dota 2 terminated gracefully")
                    return
                except subprocess.TimeoutExpired:
                    logger.warning("Graceful termination timed out, forcing kill")
            
            # Force kill
            self.process.kill()
            self.process.wait()
            logger.info("Dota 2 force killed")
            
        except Exception as e:
            logger.error("Error terminating Dota 2", error=str(e))
        
        finally:
            # Cancel monitor task
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        await self.terminate()
