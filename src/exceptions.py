"""Custom exceptions for DotaForge."""


class DotaForgeError(Exception):
    """Base exception for all DotaForge errors."""
    pass


class ConfigError(DotaForgeError):
    """Configuration-related error."""
    pass


class DotaNotFoundError(DotaForgeError):
    """Dota 2 installation not found."""
    pass


class DotaLaunchError(DotaForgeError):
    """Failed to launch Dota 2."""
    pass


class ReplayError(DotaForgeError):
    """Base exception for replay-related errors."""
    pass


class ReplayNotAvailableError(ReplayError):
    """Replay is not available (expired or missing)."""
    pass


class ReplayDownloadError(ReplayError):
    """Failed to download replay."""
    pass


class ReplayCorruptedError(ReplayError):
    """Downloaded replay file is corrupted."""
    pass


class RecordingError(DotaForgeError):
    """Base exception for recording-related errors."""
    pass


class CameraError(RecordingError):
    """Failed to control camera."""
    pass


class FFmpegError(RecordingError):
    """FFmpeg conversion failed."""
    pass


class StorageError(DotaForgeError):
    """Storage-related error."""
    pass


class APIError(DotaForgeError):
    """External API error."""
    pass


class OpenDotaError(APIError):
    """OpenDota API error."""
    pass


class TransientError(DotaForgeError):
    """Error that might be resolved by retrying."""
    pass
