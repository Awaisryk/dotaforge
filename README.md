# DotaForge

Automated Dota 2 replay recording and YouTube upload system.

## Features

- 🔍 **Auto-discovers matches** from your OpenDota profile
- 🎯 **Smart filtering**: wins only, specific heroes, min/max duration, KDA thresholds
- 🎬 **Full recording automation**: Launches Dota 2, sets camera, records, converts to MP4
- 🗑️ **Auto-cleanup**: Deletes old videos after 10 days (configurable)
- ⏰ **Scheduled runs**: Daily at configured time
- 📊 **SQLite database**: Tracks all recorded matches

## Requirements

- Windows OS
- Dota 2 installed (auto-detected or set DOTA2_PATH)
- Python 3.10+
- ffmpeg (for video conversion)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ffmpeg:**
   - Download from https://ffmpeg.org/download.html
   - Add to PATH

3. **Copy configuration:**
   ```bash
   # Edit .env with your settings
   cp .env.example .env
   ```

4. **Configure your Steam ID:**
   ```bash
   # .env
   STEAM_ACCOUNT_ID=101855970  # Your Steam32 ID
   PLAYER_NAME=YourName
   ```

## Usage

### Test the setup:
```bash
python test_phase1.py  # Test API, database, etc
python test_phase2.py  # Test Dota 2 launcher, ffmpeg, etc
python -m src.cli test  # Quick connectivity test
```

### Dry run (test without launching Dota 2):
```bash
python main.py --once --dry-run
```

### Record once:
```bash
python main.py --once
```

### Start scheduled service:
```bash
python main.py  # Runs daily at configured time
```

### CLI commands:
```bash
python -m src.cli status      # Show configuration and stats
python -m src.cli list        # List recorded matches
python -m src.cli cleanup     # Clean up old files
python -m src.cli find-dota   # Find Dota 2 installation
python -m src.cli test        # Test all components
```

## Configuration

Edit `.env` file:

```bash
# Player settings
STEAM_ACCOUNT_ID=101855970
PLAYER_NAME=Mr.Vesper

# Match filtering
MATCH_SELECTION__ONLY_WINS=false
MATCH_SELECTION__HERO_FILTER=         # e.g., "Invoker"
MATCH_SELECTION__MIN_KDA=0
MATCH_SELECTION__MIN_DURATION_SECONDS=600
MATCH_SELECTION__MAX_DURATION_SECONDS=5400

# Recording quality
RECORDING__RESOLUTION=1920x1080
RECORDING__FRAMERATE=60
RECORDING__QUALITY=high
RECORDING__CRF=18              # Lower = better quality

# Storage & cleanup
STORAGE__AUTO_DELETE_DAYS=10
STORAGE__MAX_STORAGE_GB=100
STORAGE__CLEANUP_REPLAYS=true
STORAGE__CLEANUP_TEMP=true

# Scheduling
RUN_TIME=02:00
TIMEZONE=UTC
```

## How It Works

### Week 1: Foundation ✅
- Configuration management with Pydantic
- OpenDota API integration
- Match discovery with filtering
- Replay download from Valve CDN
- SQLite database for tracking

### Week 2: Recording ✅
- Dota 2 process launcher
- Camera control for player perspective
- Native `startmovie` recording
- TGA frame capture
- FFmpeg conversion to MP4
- Full workflow orchestration

### Workflow:
1. Fetches recent matches from OpenDota API
2. Filters by your criteria (wins, heroes, duration, KDA)
3. Downloads replay from Valve CDN
4. Launches Dota 2 with replay
5. Sets camera to player perspective
6. Records gameplay using `startmovie` (TGA frames)
7. Converts frames to MP4 using ffmpeg
8. Stores in `output/` folder
9. Cleans up old files
10. Tracks in database for duplicate prevention

## Storage Requirements

- **Replay files**: ~100MB per match (auto-deleted after recording)
- **TGA frames**: ~300MB/min at 1080p60 (auto-deleted after conversion)
- **Final MP4**: ~2-3GB for 30min match at high quality
- **Recommended**: 50-100GB free space

## Troubleshooting

### Dota 2 not found:
```bash
python -m src.cli find-dota
# Then set DOTA2_PATH in .env
```

### ffmpeg not found:
- Download from https://ffmpeg.org/download.html
- Add to PATH
- Verify: `ffmpeg -version`

### No matches found:
- Check your STEAM_ACCOUNT_ID is correct
- Check your profile is public on OpenDota
- Adjust match filters (duration, KDA thresholds)

### Recording fails:
- Ensure Dota 2 is not already running
- Check logs in `logs/` folder
- Try `--dry-run` first to test configuration

## Project Structure

```
dotaforge/
├── src/
│   ├── api/opendota.py        # OpenDota API client
│   ├── core/
│   │   ├── match_finder.py    # Match filtering
│   │   ├── replay_manager.py  # Download replays
│   │   └── storage_manager.py # Cleanup & quotas
│   ├── dota/
│   │   ├── launcher.py        # Launch Dota 2
│   │   └── camera.py          # Camera control
│   ├── recorder/
│   │   ├── startmovie.py      # TGA recording
│   │   ├── ffmpeg.py          # Video conversion
│   │   └── orchestrator.py    # Full workflow
│   ├── models/match.py        # Data classes
│   ├── utils/dota_detector.py # Dota 2 auto-detect
│   ├── database.py            # SQLite tracking
│   ├── config.py              # Settings
│   ├── logger.py              # Structured logging
│   └── cli.py                 # CLI interface
├── config/
│   └── record_auto.cfg        # Dota 2 autoexec
├── main.py                    # Entry point
├── .env                       # Your configuration
└── README.md
```

## Status

✅ **Week 1**: Foundation (API, database, match finding)
✅ **Week 2**: Recording (Dota 2 automation, video capture)
⏳ **Week 3-4**: YouTube upload integration (coming soon)

## License

MIT
