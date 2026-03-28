"""Dota 2 installation auto-detection utilities."""

import json
import os
import re
from pathlib import Path
from typing import Optional, List

from src.logger import logger

# Known Steam installation paths to check
COMMON_STEAM_PATHS = [
    Path("C:/Program Files (x86)/Steam"),
    Path("C:/Program Files/Steam"),
    Path("C:/Steam"),
]

# Drive letters to check for alternative installations
DRIVE_LETTERS = "CDEFGHIJKLMNOPQRSTUVWXYZ"

DOTA2_SUBPATH = Path("steamapps/common/dota 2 beta")
DOTA2_EXE_SUBPATH = Path("game/bin/win64/dota2.exe")


def _get_library_folders_from_vdf(steam_path: Path) -> List[Path]:
    """Parse libraryfolders.vdf to get all Steam library locations."""
    vdf_path = steam_path / "steamapps/libraryfolders.vdf"
    
    if not vdf_path.exists():
        return []
    
    libraries = []
    
    try:
        with open(vdf_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse VDF format (simplified)
        # Look for "path" "..." entries
        path_pattern = r'"path"\s*"([^"]+)"'
        matches = re.findall(path_pattern, content)
        
        for match in matches:
            # Handle escaped backslashes in VDF
            path_str = match.replace("\\\\", "/").replace("\\", "/")
            path = Path(path_str)
            if path.exists():
                libraries.append(path)
    
    except Exception as e:
        logger.warning("Failed to parse libraryfolders.vdf", error=str(e))
    
    return libraries


def _find_dota2_in_path(library_path: Path) -> Optional[Path]:
    """Check if Dota 2 exists in a given Steam library path."""
    dota_path = library_path / DOTA2_SUBPATH
    exe_path = dota_path / DOTA2_EXE_SUBPATH
    
    if dota_path.exists() and exe_path.exists():
        return dota_path
    
    return None


def _get_common_paths() -> List[Path]:
    """Generate common Steam installation paths across all drives."""
    paths = []
    
    # Add known default paths
    paths.extend(COMMON_STEAM_PATHS)
    
    # Add paths on other drives
    for drive in DRIVE_LETTERS:
        if drive == "C":
            continue  # Already covered
        
        paths.append(Path(f"{drive}:/Steam"))
        paths.append(Path(f"{drive}:/Program Files (x86)/Steam"))
        paths.append(Path(f"{drive}:/Program Files/Steam"))
    
    return paths


def find_dota2_installation() -> Optional[Path]:
    """Auto-detect Dota 2 installation path.
    
    Searches in the following order:
    1. DOTA2_PATH environment variable
    2. Common Steam installation paths
    3. All library folders from libraryfolders.vdf
    4. All drive letters
    
    Returns:
        Path to Dota 2 installation directory, or None if not found
    """
    # 1. Check environment variable
    env_path = os.getenv("DOTA2_PATH")
    if env_path:
        path = Path(env_path)
        exe = path / DOTA2_EXE_SUBPATH
        if exe.exists():
            logger.info("Found Dota 2 from environment variable", path=str(path))
            return path
        else:
            logger.warning(
                "DOTA2_PATH set but executable not found",
                path=str(path),
                expected_exe=str(exe)
            )
    
    # 2. Check common Steam paths
    for steam_path in _get_common_paths():
        if not steam_path.exists():
            continue
        
        # Try direct subpath first
        result = _find_dota2_in_path(steam_path)
        if result:
            logger.info("Found Dota 2 in common path", path=str(result))
            return result
        
        # Check library folders
        libraries = _get_library_folders_from_vdf(steam_path)
        for library in libraries:
            result = _find_dota2_in_path(library)
            if result:
                logger.info(
                    "Found Dota 2 in library folder",
                    path=str(result),
                    library=str(library)
                )
                return result
    
    logger.error("Could not auto-detect Dota 2 installation")
    return None


def verify_dota2_path(path: Path) -> bool:
    """Verify that a path contains a valid Dota 2 installation.
    
    Args:
        path: Path to check
        
    Returns:
        True if valid Dota 2 installation, False otherwise
    """
    if not path.exists():
        return False
    
    exe = path / DOTA2_EXE_SUBPATH
    return exe.exists()


def get_dota2_exe_path(dota2_path: Path) -> Path:
    """Get the path to the Dota 2 executable.
    
    Args:
        dota2_path: Dota 2 installation directory
        
    Returns:
        Path to dota2.exe
    """
    return dota2_path / DOTA2_EXE_SUBPATH
