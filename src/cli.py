"""Command-line interface for DotaForge."""

import asyncio
from pathlib import Path

import click

from src.api.opendota import OpenDotaClient
from src.config import get_settings, reload_settings
from src.core.match_finder import MatchFinder
from src.core.replay_manager import ReplayManager
from src.database import Database
from src.logger import logger
from src.utils.dota_detector import find_dota2_installation


@click.group()
@click.option("--debug", is_flag=True, help="Enable verbose debugging output")
@click.pass_context
def cli(ctx, debug):
    """DotaForge - Automated Dota 2 Replay Recording"""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.option(
    "--once",
    is_flag=True,
    help="Run once and exit (don't start scheduler)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run mode - don't actually launch Dota 2"
)
def run(once, dry_run):
    """Run the recording service."""
    from main import run_single, start_scheduler
    
    if dry_run:
        click.echo("🧪 Dry run mode enabled - will not launch Dota 2")
        import os
        os.environ["DRY_RUN"] = "true"
    
    if once:
        click.echo("▶️  Running once...")
        asyncio.run(run_single())
    else:
        click.echo("🚀 Starting scheduled service...")
        start_scheduler()


@cli.command()
def status():
    """Show current status and statistics."""
    settings = get_settings()
    
    click.echo("\n" + "=" * 50)
    click.echo("📊 DOTAFORGE STATUS")
    click.echo("=" * 50)
    
    # Player info
    click.echo(f"\n👤 Player: {settings.player_name}")
    click.echo(f"🎮 Steam ID: {settings.steam_account_id}")
    
    # Dota 2 path
    if settings.dota2_path:
        click.echo(f"📁 Dota 2 Path: {settings.dota2_path}")
    else:
        click.echo("📁 Dota 2 Path: Auto-detecting...")
        dota_path = find_dota2_installation()
        if dota_path:
            click.echo(f"   Found: {dota_path}")
        else:
            click.echo("   ⚠️  Not found - will try again at runtime")
    
    # Match selection settings
    click.echo(f"\n🎯 Match Selection:")
    click.echo(f"   Matches per day: {settings.match_selection.matches_per_day}")
    click.echo(f"   Only wins: {settings.match_selection.only_wins}")
    click.echo(f"   Hero filter: {settings.match_selection.hero_filter or 'None'}")
    click.echo(f"   Min duration: {settings.match_selection.min_duration_seconds // 60} min")
    click.echo(f"   Max duration: {settings.match_selection.max_duration_seconds // 60} min")
    click.echo(f"   Min KDA: {settings.match_selection.min_kda}")
    
    # Recording settings
    click.echo(f"\n🎬 Recording:")
    click.echo(f"   Resolution: {settings.recording.resolution}")
    click.echo(f"   Framerate: {settings.recording.framerate} fps")
    click.echo(f"   Quality: {settings.recording.quality} (CRF {settings.recording.crf})")
    
    # Storage
    click.echo(f"\n💾 Storage:")
    click.echo(f"   Auto-delete after: {settings.storage.auto_delete_days} days")
    click.echo(f"   Max storage: {settings.storage.max_storage_gb} GB")
    
    # Schedule
    click.echo(f"\n⏰ Schedule: {settings.run_time} ({settings.timezone})")
    
    # Database stats
    async def show_stats():
        db = Database()
        await db.init()
        stats = await db.get_stats()
        
        click.echo(f"\n📈 Recording Stats:")
        click.echo(f"   Total recorded: {stats.get('total_success', 0)}")
        click.echo(f"   Failed: {stats.get('total_failed', 0)}")
        click.echo(f"   Average KDA: {stats.get('average_kda', 0)}")
        
        if stats.get('last_recorded'):
            click.echo(f"\n🎮 Last recorded: {stats['last_recorded']['match_id']}")
            click.echo(f"   Hero: {stats['last_recorded']['hero']}")
            click.echo(f"   Time: {stats['last_recorded']['recorded_at']}")
    
    asyncio.run(show_stats())
    
    click.echo("\n" + "=" * 50)


@cli.command()
@click.option(
    "--days",
    default=None,
    type=int,
    help="Delete videos older than N days (uses config default if not set)"
)
def cleanup(days):
    """Clean up old files and videos."""
    settings = get_settings()
    delete_days = days or settings.storage.auto_delete_days
    
    click.echo(f"🧹 Cleaning up files older than {delete_days} days...")
    
    # Clean up old database records
    async def do_cleanup():
        db = Database()
        await db.init()
        
        deleted_db = await db.delete_old_records(delete_days)
        click.echo(f"   🗑️  Deleted {deleted_db} old database records")
        
        # Clean up old video files
        from src.core.storage_manager import StorageManager
        storage = StorageManager(settings.storage)
        
        deleted_videos = await storage.cleanup_old_videos(delete_days)
        click.echo(f"   🗑️  Deleted {deleted_videos} old video files")
        
        # Clean up replays if enabled
        if settings.storage.cleanup_replays:
            replays_dir = Path("replays")
            if replays_dir.exists():
                count = 0
                for replay in replays_dir.glob("*.dem"):
                    replay.unlink()
                    count += 1
                click.echo(f"   🗑️  Deleted {count} replay files")
    
    asyncio.run(do_cleanup())
    
    click.echo("\n✅ Cleanup complete!")


@cli.command()
@click.option(
    "--days",
    default=7,
    help="Show matches from last N days"
)
def list(days):
    """List recorded matches."""
    async def do_list():
        db = Database()
        await db.init()
        
        matches = await db.get_recent_matches(days=days)
        
        if not matches:
            click.echo(f"\n📭 No matches recorded in the last {days} days")
            return
        
        click.echo(f"\n📼 Recorded Matches (Last {days} days):\n")
        click.echo(f"{'Match ID':<12} {'Hero':<20} {'KDA':<8} {'Result':<8} {'Status':<10} {'Date'}")
        click.echo("-" * 80)
        
        for match in matches:
            result = "Win" if match.is_win else "Loss"
            date_str = match.recorded_at.strftime("%Y-%m-%d %H:%M")
            hero = match.hero_name or "Unknown"
            
            click.echo(
                f"{match.match_id:<12} "
                f"{hero:<20} "
                f"{match.kda:<8.1f} "
                f"{result:<8} "
                f"{match.status:<10} "
                f"{date_str}"
            )
        
        click.echo(f"\nTotal: {len(matches)} matches")
    
    asyncio.run(do_list())


@cli.command()
def find_dota():
    """Attempt to find Dota 2 installation."""
    click.echo("🔍 Searching for Dota 2 installation...")
    
    dota_path = find_dota2_installation()
    
    if dota_path:
        click.echo(f"\n✅ Found Dota 2 at:")
        click.echo(f"   {dota_path}")
        click.echo(f"\n📝 Add this to your .env file:")
        click.echo(f"   DOTA2_PATH={dota_path}")
    else:
        click.echo("\n❌ Could not find Dota 2 installation")
        click.echo("\nPlease manually set DOTA2_PATH in your .env file")
        click.echo("Example: DOTA2_PATH=E:/Steam/steamapps/common/dota 2 beta")


@cli.command()
def test():
    """Test configuration and connectivity."""
    click.echo("🧪 Testing DotaForge configuration...\n")
    
    # Test settings
    try:
        settings = get_settings()
        click.echo("✅ Settings loaded successfully")
        click.echo(f"   Player: {settings.player_name} ({settings.steam_account_id})")
    except Exception as e:
        click.echo(f"❌ Failed to load settings: {e}")
        return
    
    # Test OpenDota API
    click.echo("\n🌐 Testing OpenDota API...")
    async def test_api():
        try:
            client = OpenDotaClient()
            matches = await client.get_recent_matches(settings.steam_account_id)
            click.echo(f"✅ API connection successful")
            click.echo(f"   Found {len(matches)} recent matches")
            await client.close()
        except Exception as e:
            click.echo(f"❌ API connection failed: {e}")
    
    asyncio.run(test_api())
    
    # Test database
    click.echo("\n💾 Testing database...")
    async def test_db():
        try:
            db = Database()
            await db.init()
            click.echo("✅ Database connection successful")
        except Exception as e:
            click.echo(f"❌ Database connection failed: {e}")
    
    asyncio.run(test_db())
    
    # Test Dota 2 detection
    click.echo("\n🎮 Testing Dota 2 detection...")
    if settings.dota2_path:
        click.echo(f"✅ Dota 2 path configured: {settings.dota2_path}")
    else:
        dota_path = find_dota2_installation()
        if dota_path:
            click.echo(f"✅ Auto-detected Dota 2 at: {dota_path}")
        else:
            click.echo("⚠️  Dota 2 not found - will attempt at runtime")
    
    click.echo("\n✅ Test complete!")


if __name__ == "__main__":
    cli()
