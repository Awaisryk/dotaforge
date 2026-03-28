"""Test script for DotaForge Phase 2 - Recording."""

import asyncio
from pathlib import Path

from src.config import get_settings
from src.dota.camera import CameraController
from src.dota.launcher import DotaLauncher
from src.logger import logger
from src.recorder.ffmpeg import FFmpegConverter
from src.recorder.startmovie import StartMovieRecorder
from src.utils.dota_detector import find_dota2_installation


async def test_dota_launcher():
    """Test Dota 2 launcher detection."""
    print("\n" + "=" * 60)
    print("TEST 1: Dota 2 Launcher & Auto-Detection")
    print("=" * 60)
    
    try:
        dota_path = find_dota2_installation()
        if dota_path:
            print(f"✅ Found Dota 2 at: {dota_path}")
            
            # Try to initialize launcher
            launcher = DotaLauncher(dota_path)
            print(f"✅ Launcher initialized successfully")
            print(f"   Executable: {launcher.exe_path}")
        else:
            print("⚠️  Dota 2 not auto-detected")
            print("   Set DOTA2_PATH in .env to specify location")
    except Exception as e:
        print(f"❌ Launcher test failed: {e}")
        return False
    
    return True


async def test_camera_controller():
    """Test camera controller."""
    print("\n" + "=" * 60)
    print("TEST 2: Camera Controller")
    print("=" * 60)
    
    try:
        camera = CameraController()
        
        # Test command generation
        commands = camera.generate_commands(player_slot=0, match_id=12345)
        print("✅ Generated camera commands:")
        print("   First 3 lines:")
        for line in commands.split('\n')[:3]:
            print(f"     {line}")
        
        # Test file writing
        cmd_file = camera.write_command_file(player_slot=0, match_id=12345)
        print(f"✅ Wrote commands to: {cmd_file}")
        
        # Clean up
        if cmd_file.exists():
            cmd_file.unlink()
        
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False
    
    return True


async def test_recorder():
    """Test StartMovie recorder."""
    print("\n" + "=" * 60)
    print("TEST 3: StartMovie Recorder")
    print("=" * 60)
    
    try:
        recorder = StartMovieRecorder()
        
        # Test command generation
        start_cmd = recorder.generate_start_command(match_id=12345)
        print(f"✅ Start command: {start_cmd[:60]}...")
        
        stop_cmd = recorder.generate_stop_command()
        print(f"✅ Stop command: {stop_cmd}")
        
        # Test file pattern
        pattern = recorder.get_frame_pattern(12345)
        print(f"✅ Frame pattern: {pattern}")
        
        # Test frame counting (will be 0 since no frames exist)
        count = recorder.get_frame_count(12345)
        print(f"✅ Frame count (expected 0): {count}")
        
    except Exception as e:
        print(f"❌ Recorder test failed: {e}")
        return False
    
    return True


async def test_ffmpeg():
    """Test FFmpeg converter."""
    print("\n" + "=" * 60)
    print("TEST 4: FFmpeg Converter")
    print("=" * 60)
    
    try:
        # Try to initialize
        converter = FFmpegConverter()
        print("✅ FFmpeg found and initialized")
        
        # Check availability
        if converter.is_available():
            print("✅ FFmpeg is available for use")
        else:
            print("❌ FFmpeg is not available")
            return False
        
        # Note: We won't test actual conversion since we don't have frames
        print("ℹ️  Skipping actual conversion test (no frames available)")
        
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        print("   Please install ffmpeg: https://ffmpeg.org/download.html")
        return False
    
    return True


async def test_integration():
    """Test component integration."""
    print("\n" + "=" * 60)
    print("TEST 5: Component Integration")
    print("=" * 60)
    
    try:
        settings = get_settings()
        
        # Check if we can build an orchestrator
        dota_path = settings.dota2_path or find_dota2_installation()
        
        if not dota_path:
            print("⚠️  Dota 2 not found - skipping integration test")
            print("   Set DOTA2_PATH in .env to run full integration")
            return True
        
        print("✅ Found Dota 2 installation")
        
        # Initialize components
        launcher = DotaLauncher(dota_path)
        print("✅ Launcher ready")
        
        camera = CameraController()
        print("✅ Camera ready")
        
        recorder = StartMovieRecorder()
        print("✅ Recorder ready")
        
        converter = FFmpegConverter()
        print("✅ Converter ready")
        
        # Note: We won't actually run the workflow as it would launch Dota 2
        print("\nℹ️  Integration test successful")
        print("   Full workflow test requires manually running with --dry-run")
        print("   Command: python main.py --once --dry-run")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False
    
    return True


async def show_workflow_info():
    """Show information about the recording workflow."""
    print("\n" + "=" * 60)
    print("📋 RECORDING WORKFLOW INFO")
    print("=" * 60)
    
    settings = get_settings()
    
    print("\n🔧 Configuration:")
    print(f"   Resolution: {settings.recording.resolution}")
    print(f"   Framerate: {settings.recording.framerate} fps")
    print(f"   Quality: {settings.recording.quality} (CRF {settings.recording.crf})")
    
    print("\n📝 Workflow Steps:")
    print("   1. Download replay from Valve CDN")
    print("   2. Launch Dota 2 with replay loaded")
    print("   3. Wait for game to load")
    print("   4. Set camera to player perspective")
    print("   5. Wait for hero spawn (~10s)")
    print("   6. Start TGA recording (startmovie)")
    print("   7. Play full match duration")
    print("   8. Stop recording (endmovie)")
    print("   9. Close Dota 2")
    print("  10. Convert TGA → MP4 with ffmpeg")
    print("  11. Clean up temporary files")
    
    print("\n⚠️  Important Notes:")
    print("   - Dota 2 must be installed and accessible")
    print("   - ffmpeg must be installed for video conversion")
    print("   - First run should use --dry-run mode to test")
    print("   - Recording happens in real-time (1x speed)")
    print("   - Temporary TGA files are large (~300MB/min at 1080p60)")
    print("   - Final MP4 will be much smaller (~2-3GB for 30min match)")
    
    print("\n🚀 To run a real recording:")
    print("   python main.py --once")
    
    print("\n🧪 To test without launching Dota 2:")
    print("   python main.py --once --dry-run")


async def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n" + "🎬 " + "=" * 56)
    print("   DOTAFORGE PHASE 2 TEST SUITE")
    print("   (Dota 2 Automation & Recording)")
    print("=" * 58 + " 🎬")
    
    tests = [
        ("Dota 2 Launcher", test_dota_launcher),
        ("Camera Controller", test_camera_controller),
        ("StartMovie Recorder", test_recorder),
        ("FFmpeg Converter", test_ffmpeg),
        ("Integration", test_integration),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Show workflow info
    await show_workflow_info()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 2 is ready.")
        print("\nNext steps:")
        print("  1. Ensure Dota 2 is installed")
        print("  2. Install ffmpeg if not already installed")
        print("  3. Run with --dry-run first: python main.py --once --dry-run")
        print("  4. Then run for real: python main.py --once")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
