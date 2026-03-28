"""Test script for DotaForge Phase 1."""

import asyncio
from pathlib import Path

from src.api.opendota import OpenDotaClient
from src.config import get_settings
from src.core.match_finder import MatchFinder
from src.core.replay_manager import ReplayManager
from src.database import Database
from src.logger import logger
from src.utils.dota_detector import find_dota2_installation


async def test_configuration():
    """Test that configuration loads correctly."""
    print("\n" + "=" * 60)
    print("TEST 1: Configuration")
    print("=" * 60)
    
    try:
        settings = get_settings()
        print(f"✅ Settings loaded successfully")
        print(f"   Player: {settings.player_name}")
        print(f"   Steam ID: {settings.steam_account_id}")
        print(f"   Dota 2 Path: {settings.dota2_path or 'Auto-detect'}")
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return False
    
    return True


async def test_dota_detection():
    """Test Dota 2 auto-detection."""
    print("\n" + "=" * 60)
    print("TEST 2: Dota 2 Auto-Detection")
    print("=" * 60)
    
    try:
        dota_path = find_dota2_installation()
        if dota_path:
            print(f"✅ Found Dota 2 at: {dota_path}")
        else:
            print("⚠️  Dota 2 not auto-detected (will try at runtime)")
    except Exception as e:
        print(f"⚠️  Error during detection: {e}")
    
    return True


async def test_database():
    """Test database initialization."""
    print("\n" + "=" * 60)
    print("TEST 3: Database")
    print("=" * 60)
    
    try:
        db = Database()
        await db.init()
        print("✅ Database initialized successfully")
        
        # Test write
        from src.models.match import Match
        test_match = Match(
            match_id=12345,
            player_slot=0,
            hero_id=1,
            hero_name="Test Hero",
            duration_seconds=1800
        )
        await db.mark_processed(test_match, Path("test.mp4"), "success")
        print("✅ Test write successful")
        
        # Test read
        is_processed = await db.is_processed(12345)
        print(f"✅ Test read successful (is_processed={is_processed})")
        
        # Clean up
        import aiosqlite
        async with aiosqlite.connect("data/processed.db") as conn:
            await conn.execute("DELETE FROM processed_matches WHERE match_id = 12345")
            await conn.commit()
        print("✅ Test cleanup successful")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True


async def test_opendota_api():
    """Test OpenDota API connection."""
    print("\n" + "=" * 60)
    print("TEST 4: OpenDota API")
    print("=" * 60)
    
    settings = get_settings()
    client = OpenDotaClient()
    
    try:
        print(f"Fetching recent matches for account {settings.steam_account_id}...")
        matches = await client.get_recent_matches(settings.steam_account_id)
        
        if matches:
            print(f"✅ Found {len(matches)} recent matches")
            match = matches[0]
            print(f"   Latest: {match.hero_name} - KDA {match.kda} - {match.duration_formatted}")
        else:
            print("⚠️  No recent matches found")
        
        await client.close()
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        await client.close()
        return False
    
    return True


async def test_match_finder():
    """Test match finding and filtering."""
    print("\n" + "=" * 60)
    print("TEST 5: Match Finder")
    print("=" * 60)
    
    settings = get_settings()
    client = OpenDotaClient()
    db = Database()
    await db.init()
    
    try:
        finder = MatchFinder(client, db)
        match = await finder.find_next_match()
        
        if match:
            print(f"✅ Found eligible match to record:")
            print(f"   Match ID: {match.match_id}")
            print(f"   Hero: {match.hero_name}")
            print(f"   KDA: {match.kda}")
            print(f"   Duration: {match.duration_formatted}")
            print(f"   Result: {'Win' if match.is_win else 'Loss'}")
        else:
            print("ℹ️  No eligible unprocessed matches found")
            print("   (This is normal if all recent matches were already recorded)")
        
        await client.close()
        
    except Exception as e:
        print(f"❌ Match finder test failed: {e}")
        await client.close()
        return False
    
    return True


async def test_replay_manager():
    """Test replay download capability."""
    print("\n" + "=" * 60)
    print("TEST 6: Replay Manager (API only)")
    print("=" * 60)
    
    settings = get_settings()
    client = OpenDotaClient()
    
    try:
        # Get a recent match
        matches = await client.get_recent_matches(settings.steam_account_id)
        
        if not matches:
            print("⚠️  No matches to test with")
            await client.close()
            return True
        
        test_match = matches[0]
        print(f"Testing with match {test_match.match_id}...")
        
        # Check if replay URL is available
        replay_url = await client.get_replay_url(test_match.match_id)
        
        if replay_url:
            print(f"✅ Replay URL available:")
            print(f"   {replay_url[:60]}...")
        else:
            print("ℹ️  Replay not available (expired or still processing)")
        
        await client.close()
        
    except Exception as e:
        print(f"❌ Replay manager test failed: {e}")
        await client.close()
        return False
    
    return True


async def run_all_tests():
    """Run all Phase 1 tests."""
    print("\n" + "🎬 " + "=" * 56)
    print("   DOTAFORGE PHASE 1 TEST SUITE")
    print("=" * 58 + " 🎬")
    
    tests = [
        ("Configuration", test_configuration),
        ("Dota 2 Detection", test_dota_detection),
        ("Database", test_database),
        ("OpenDota API", test_opendota_api),
        ("Match Finder", test_match_finder),
        ("Replay Manager", test_replay_manager),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
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
        print("\n🎉 All tests passed! Phase 1 is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
