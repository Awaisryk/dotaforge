# DotaForge Testing Guide

## Pre-Flight Checklist

Before testing, ensure:

1. **Dota 2 is installed** - Can you launch it normally?
2. **Steam is running** - Dota 2 needs Steam to authenticate
3. **ffmpeg installed** - Run `ffmpeg -version` in terminal
4. **Disk space** - Need ~10GB free for a test recording
5. **Close Dota 2** - Must not be running before test

## Phase 1: Static Tests (Safe)

```bash
# 1. Test Phase 1 components (API, DB, etc)
python test_phase1.py

# 2. Test Phase 2 components (Dota 2 detection, ffmpeg)
python test_phase2.py

# 3. Quick connectivity test
python -m src.cli test
```

Expected: All tests pass, Dota 2 path found, ffmpeg detected.

## Phase 2: Dry Run Test (Safe - No Dota 2 Launch)

```bash
# This tests the workflow WITHOUT launching Dota 2
python main.py --once --dry-run
```

Expected output:
- ✅ Downloads replay
- ✅ Says "Dry run - skipping actual recording"
- ✅ Cleans up replay file
- ✅ Marks match as processed

## Phase 3: End-to-End Test (Real - Launches Dota 2)

⚠️ **WARNING**: This will:
- Launch Dota 2
- Take over your screen for ~40 minutes
- Record a full match
- Create a large video file

**Before you run:**
1. Close all other apps
2. Ensure you won't need your PC for ~45 min
3. Pick a SHORT match (< 30 min recommended for first test)

```bash
# Run the full workflow ONCE
python main.py --once
```

**What will happen:**
1. Downloads replay (~30 seconds)
2. Launches Dota 2 (~10 seconds)
3. Loads replay (~15 seconds)
4. Waits for game start (~10 seconds)
5. Starts recording
6. Plays match at 1x speed (~match duration + 1 min)
7. Stops recording
8. Closes Dota 2
9. Converts frames to MP4 (~5-10 min)
10. Saves to `output/MATCH_ID.mp4`

## Phase 4: Validation

After test completes, check:

```bash
# 1. Check output folder
ls -lh output/
# Should see: MATCH_ID.mp4 (2-3GB)

# 2. Check video plays
# Double-click the MP4 file - should be a Dota 2 match

# 3. Check database
python -m src.cli list
# Should show the match as "success"

# 4. Check logs
cat logs/dotaforge-$(date +%Y-%m-%d).log
```

## Phase 5: Scheduled Mode (Optional)

If Phase 4 worked:

```bash
# Start the scheduler (runs daily at configured time)
python main.py

# To stop: Press Ctrl+C
```

## Troubleshooting

### "Dota 2 not found"
```bash
# Find it manually
python -m src.cli find-dota

# Or set in .env:
# DOTA2_PATH=E:/Steam/steamapps/common/dota 2 beta
```

### "ffmpeg not found"
- Download from https://ffmpeg.org/download.html
- Add to PATH or place in project folder

### Dota 2 launches but doesn't load replay
- Check `logs/` folder for errors
- Verify replay file exists: `ls -lh replays/`
- Check autoexec loaded: Look for "[DOTAFORGE]" messages in console

### Recording starts but stops early
- Check disk space: `df -h` or check drive properties
- Check logs for "Disk full" errors
- Reduce quality in .env: `RECORDING__QUALITY=medium`

### Video conversion fails
- Check ffmpeg is working: `ffmpeg -version`
- Check temp frames exist: `ls temp/ | head`
- Try manual conversion (see below)

### Manual ffmpeg test
```bash
# If you have frames in temp/ from a failed run:
ffmpeg -framerate 60 -i "temp/MATCHID_%04d.tga" \
       -c:v libx264 -preset slow -crf 18 \
       -pix_fmt yuv420p \
       output/manual_test.mp4
```

## Debugging Failed Runs

```bash
# Check what happened
tail -100 logs/dotaforge-$(date +%Y-%m-%d).log

# Check database status
python -m src.cli list

# Check storage
python -m src.cli status
```

## Quick Smoke Test Script

Save this as `smoke_test.py`:

```python
import asyncio
from src.api.opendota import OpenDotaClient
from src.config import get_settings

async def smoke_test():
    settings = get_settings()
    client = OpenDotaClient()
    
    print("Fetching recent matches...")
    matches = await client.get_recent_matches(settings.steam_account_id)
    
    if matches:
        print(f"✅ Found {len(matches)} matches")
        m = matches[0]
        print(f"   Latest: {m.hero_name} - {m.duration_formatted}")
        
        # Check replay availability
        url = await client.get_replay_url(m.match_id)
        if url:
            print(f"✅ Replay available")
            print(f"   Duration: {m.duration_formatted}")
            print(f"   This match is ready to record!")
        else:
            print("⚠️  Replay not available (too old)")
    else:
        print("❌ No matches found")
    
    await client.close()

asyncio.run(smoke_test())
```

## Recommended First Recording

For your first real test:

1. **Pick a short match** (< 30 minutes)
2. **Run during downtime** (you can't use PC during recording)
3. **Have 10GB free space**
4. **Keep Task Manager open** to monitor resources
5. **Don't panic** if it seems stuck - it's working!

## Expected Timeline

For a 30-minute match:
- Download: 30s
- Launch + Load: 30s
- Recording: 31min (match + buffer)
- Conversion: 5-10min
- **Total: ~40-45 minutes**

## Success Criteria

✅ End-to-end test is successful if:
1. No errors in logs
2. `output/` folder has a .mp4 file
3. Video plays correctly
4. Match appears in `python -m src.cli list` as "success"
5. You can watch your gameplay!

Ready to run your first test?
