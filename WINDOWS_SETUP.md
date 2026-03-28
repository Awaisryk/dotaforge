# DotaForge Windows Setup - Copy & Paste Guide

## Step 1: Open PowerShell as Administrator

Right-click Start button → Windows PowerShell (Admin) or Terminal (Admin)

## Step 2: Clone Repository

```powershell
# Navigate to where you want the project
cd C:\Users\%USERNAME%\Documents

# Clone the repository
git clone https://github.com/Awaisryk/dotaforge.git

# Enter the directory
cd dotaforge
```

## Step 3: Check Python Installation

```powershell
# Check if Python is installed (should show 3.10 or higher)
python --version

# If not installed, download from https://www.python.org/downloads/
# IMPORTANT: Check "Add Python to PATH" during installation!
```

## Step 4: Install Dependencies

```powershell
# Install required packages
pip install -r requirements.txt
```

## Step 5: Install ffmpeg

```powershell
# Option A: Using chocolatey (recommended)
# First install chocolatey if you don't have it:
# https://chocolatey.org/install
# Then run:
choco install ffmpeg

# Option B: Manual installation
# 1. Download from https://ffmpeg.org/download.html (Windows builds)
# 2. Extract to C:\ffmpeg
# 3. Add C:\ffmpeg\bin to your PATH environment variable
```

## Step 6: Verify ffmpeg Installation

```powershell
# Check ffmpeg is working
ffmpeg -version

# Should show version info. If not, restart PowerShell and try again.
```

## Step 7: Configure Environment

```powershell
# Copy the example environment file
copy .env.example .env

# Edit the .env file (use Notepad or any text editor)
notepad .env
```

**Edit these values in .env:**
```
STEAM_ACCOUNT_ID=101855970
PLAYER_NAME=Mr.Vesper

# IMPORTANT: Set your Dota 2 path (find it first - see below)
# Common locations:
# DOTA2_PATH=C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta
# Or:
# DOTA2_PATH=D:\Steam\steamapps\common\dota 2 beta
# Or wherever yours is installed
```

**To find your Dota 2 path:**
```powershell
# Run this to auto-detect
python -c "from src.utils.dota_detector import find_dota2_installation; print(find_dota2_installation())"

# If it finds it, copy that path to your .env file
```

## Step 8: Test Phase 1 (API & Database)

```powershell
python test_phase1.py
```

**Expected output:**
- ✅ PASS - Configuration
- ✅ PASS - Dota 2 Detection (or ⚠️ if not found, that's ok)
- ✅ PASS - Database
- ✅ PASS - OpenDota API
- ✅ PASS - Match Finder
- ✅ PASS - Replay Manager

## Step 9: Test Phase 2 (Recording Components)

```powershell
python test_phase2.py
```

**Expected output:**
- ✅ PASS - Dota 2 Launcher
- ✅ PASS - Camera Controller
- ✅ PASS - StartMovie Recorder
- ✅ PASS - FFmpeg Converter
- ✅ PASS - Integration

## Step 10: Check CLI Status

```powershell
python -m src.cli status
```

This will show your current configuration and stats.

## Step 11: Dry Run Test (IMPORTANT - No Dota 2 Launch)

```powershell
# This tests everything EXCEPT launching Dota 2
$env:DRY_RUN = "true"
python main.py --once
```

**What this does:**
- Connects to OpenDota API
- Downloads replay file
- Says "Dry run - skipping actual recording"
- Verifies all components work

**If this works, you're ready for the real test!**

## Step 12: End-to-End Recording Test (REAL TEST)

⚠️ **BEFORE YOU RUN THIS:**
- Close Dota 2 completely (check Task Manager)
- Make sure you have 10GB free disk space
- Pick a SHORT match for first test (< 30 minutes)
- You won't be able to use your PC for ~40 minutes
- Keep Task Manager open to monitor

```powershell
# Remove dry run flag
Remove-Item Env:\DRY_RUN

# Run the full recording workflow
python main.py --once
```

**What will happen:**
1. Downloads replay from Valve CDN (~30 seconds)
2. Launches Dota 2 (~10 seconds)
3. Loads the replay (~15 seconds)
4. Waits for game to start (~10 seconds)
5. Starts recording TGA frames (takes match duration + 1 minute)
6. Stops recording
7. Closes Dota 2
8. Converts TGA → MP4 with ffmpeg (~5-10 minutes)
9. Saves to `output\MATCH_ID.mp4`

**Total time: ~40-45 minutes for a 30-minute match**

## Step 13: Verify the Recording

```powershell
# List output directory
ls output\

# Check the video file exists and plays
# Double-click the .mp4 file to verify

# Check database
python -m src.cli list
```

## Step 14: Enable Daily Recording (Optional)

```powershell
# This will run every day at the configured time (default: 2 AM)
python main.py

# To stop: Press Ctrl+C
```

## Troubleshooting

### "Dota 2 not found"
```powershell
# Manually set the path in .env:
# Edit .env and add:
# DOTA2_PATH=C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta
```

### "ffmpeg not found"
```powershell
# Download from https://www.gnu.org/software/ffmpeg/
# Or use chocolatey: choco install ffmpeg
# Then restart PowerShell
```

### "No matches to record"
```powershell
# Check that you have recent matches on OpenDota:
# https://www.opendota.com/players/101855970

# If no recent matches, play some games first!
# Or adjust DAYS_BACK in .env to look further back
```

### Recording fails partway
```powershell
# Check logs
cat logs\dotaforge-$(Get-Date -Format "yyyy-MM-dd").log

# Check disk space
Get-PSDrive C | Select-Object Free

# If disk is full, clean up:
python -m src.cli cleanup
```

### Match too long
Edit `.env` and reduce max duration:
```
MATCH_SELECTION__MAX_DURATION_SECONDS=1800
```
This will only record matches under 30 minutes.

## Success Criteria

✅ **Test is successful if:**
1. Video file exists in `output\` folder
2. Video plays correctly and shows your gameplay
3. `python -m src.cli list` shows match as "success"
4. No errors in log files

## Commands Summary

```powershell
# Quick reference - copy these as needed:

# Test everything
python test_phase1.py
python test_phase2.py

# Check status
python -m src.cli status

# Dry run (safe test)
$env:DRY_RUN = "true"
python main.py --once

# Real recording
Remove-Item Env:\DRY_RUN
python main.py --once

# List recorded matches
python -m src.cli list

# Clean up old files
python -m src.cli cleanup

# Find Dota 2
python -m src.cli find-dota

# Scheduled mode (runs daily)
python main.py
```

---

**Ready to test? Start with Step 1 and work your way down!**
