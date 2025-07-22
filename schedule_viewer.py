# schedule_viewer.py - View scheduled posts timing
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import pathlib

# Load environment variables
dotenv_path = pathlib.Path(__file__).parent / ".." / ".streamlit" / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

DB_FILE = "campaign.db"

def view_schedule():
    """Display all scheduled posts with their timing"""
    print("📅 SCHEDULED POSTS OVERVIEW")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get all posts ordered by schedule time
        cursor.execute("""
            SELECT id, platform, text, scheduled, posted, permalink 
            FROM posts 
            ORDER BY scheduled ASC
        """)
        
        posts = cursor.fetchall()
        conn.close()
        
        if not posts:
            print("❌ No scheduled posts found")
            print("💡 Run the main app and click 'Generate & Schedule' first")
            return
        
        now = datetime.now(timezone.utc)
        due_count = 0
        future_count = 0
        posted_count = 0
        
        for i, (post_id, platform, text, scheduled_str, posted, permalink) in enumerate(posts, 1):
            # Parse scheduled time
            scheduled_time = datetime.fromisoformat(scheduled_str.replace('Z', '+00:00'))
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
            
            # Calculate time difference
            time_diff = scheduled_time - now
            
            # Status indicators
            if posted:
                status = "✅ POSTED"
                posted_count += 1
            elif scheduled_time <= now:
                status = "🔥 DUE NOW"
                due_count += 1
            else:
                status = f"⏰ IN {format_time_diff(time_diff)}"
                future_count += 1
            
            # Platform emoji
            platform_emoji = {
                'x': '🐦',
                'twitter': '🐦',
                'reddit': '🔴',
                'linkedin': '💼'
            }.get(platform.lower(), '📱')
            
            print(f"{i:2d}. {platform_emoji} {platform.upper():<8} | {status:<20}")
            print(f"    📅 Scheduled: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"    📝 Text: {text[:60]}...")
            if permalink:
                print(f"    🔗 URL: {permalink}")
            print()
        
        # Summary
        print("=" * 80)
        print(f"📊 SUMMARY:")
        print(f"   ✅ Posted: {posted_count}")
        print(f"   🔥 Due now: {due_count}")
        print(f"   ⏰ Future: {future_count}")
        print(f"   📝 Total: {len(posts)}")
        
        if due_count > 0:
            print(f"\n💡 {due_count} posts are ready to send! Start the scheduler in your app.")
            
    except Exception as e:
        print(f"❌ Error reading schedule: {e}")

def format_time_diff(td):
    """Format timedelta in human-readable format"""
    if td.days > 0:
        return f"{td.days}d {td.seconds//3600}h"
    elif td.seconds >= 3600:
        return f"{td.seconds//3600}h {(td.seconds%3600)//60}m"
    elif td.seconds >= 60:
        return f"{td.seconds//60}m"
    else:
        return f"{td.seconds}s"

def show_posting_schedule():
    """Show when the scheduler posts"""
    print("🕐 POSTING SCHEDULE EXPLANATION")
    print("=" * 60)
    print("📋 How the scheduler works:")
    print("   • Checks for due posts every 1 minute")
    print("   • Checks for new comments every 10 minutes")
    print("   • Posts are scheduled across 14 days")
    print("   • Each platform posts once per day")
    print()
    print("🎯 Current schedule pattern:")
    
    platforms = [
        {"platform": "x", "prompt": "Twitter/X posts"},
        {"platform": "reddit", "prompt": "Reddit posts to r/productivity"},
        {"platform": "linkedin", "prompt": "LinkedIn professional posts"}
    ]
    
    base_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    for day in range(3):  # Show first 3 days as example
        print(f"📅 Day {day + 1} ({(base_time + timedelta(days=day)).strftime('%Y-%m-%d')}):")
        for p in platforms:
            schedule_time = base_time + timedelta(days=day)
            print(f"   • {p['platform'].upper():<8}: {schedule_time.strftime('%H:%M UTC')}")
        print()

if __name__ == "__main__":
    view_schedule()
    print()
    show_posting_schedule()
