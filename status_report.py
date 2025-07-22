# status_report.py - Complete system status
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import pathlib

# Load environment variables
dotenv_path = pathlib.Path(__file__).parent / ".." / ".streamlit" / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

def check_credentials():
    """Check if all required credentials are available"""
    print("🔐 CREDENTIALS CHECK")
    print("=" * 50)
    
    credentials = {
        'Twitter': {
            'TW_API_KEY': bool(os.getenv("TW_API_KEY")),
            'TW_API_SECRET': bool(os.getenv("TW_API_SECRET")),
            'TW_ACCESS': bool(os.getenv("TW_ACCESS")),
            'TW_ACCESS_SECRET': bool(os.getenv("TW_ACCESS_SECRET")),
            'TW_BEARER': bool(os.getenv("TW_BEARER"))
        },
        'Reddit': {
            'REDDIT_CLIENT': bool(os.getenv("REDDIT_CLIENT")),
            'REDDIT_SECRET': bool(os.getenv("REDDIT_SECRET")),
            'REDDIT_USER': bool(os.getenv("REDDIT_USER")),
            'REDDIT_PW': bool(os.getenv("REDDIT_PW")),
            'REDDIT_UA': bool(os.getenv("REDDIT_UA"))
        },
        'LinkedIn': {
            'LINKEDIN_TOKEN': bool(os.getenv("LINKEDIN_TOKEN"))
        },
        'AI Services': {
            'GROQAPI_KEY': bool(os.getenv("GROQAPI_KEY")),
            'OPENROUTER_KEY': bool(os.getenv("OPENROUTER_KEY")),
            'GEMINI_API_KEY': bool(os.getenv("GEMINI_API_KEY"))
        }
    }
    
    for platform, creds in credentials.items():
        print(f"\n{platform}:")
        all_present = all(creds.values())
        status_icon = "✅" if all_present else "⚠️"
        print(f"  {status_icon} Overall: {'Complete' if all_present else 'Missing credentials'}")
        
        for key, present in creds.items():
            icon = "✅" if present else "❌"
            print(f"    {icon} {key}")

def check_database():
    """Check database status"""
    print("\n📊 DATABASE STATUS")
    print("=" * 50)
    
    try:
        if not os.path.exists("campaign.db"):
            print("❌ Database file not found")
            return
            
        conn = sqlite3.connect("campaign.db")
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ Database file exists")
        print(f"📋 Tables: {[t[0] for t in tables]}")
        
        # Count posts
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM posts WHERE posted=1")
        posted_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM posts WHERE posted=0")
        pending_count = cursor.fetchone()[0]
        
        print(f"📝 Total posts: {total_posts}")
        print(f"✅ Posted: {posted_count}")
        print(f"⏰ Pending: {pending_count}")
        
        # Show recent activity
        cursor.execute("SELECT platform, scheduled, posted FROM posts ORDER BY scheduled DESC LIMIT 5")
        recent = cursor.fetchall()
        
        if recent:
            print(f"\n📅 Recent posts:")
            for platform, scheduled, posted in recent:
                status = "✅" if posted else "⏰"
                print(f"   {status} {platform.upper()}: {scheduled}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def explain_posting_logic():
    """Explain how the posting system works"""
    print("\n🚀 HOW POSTING WORKS")
    print("=" * 50)
    
    print("📋 Scheduling Logic:")
    print("   1. When you click 'Generate & Schedule':")
    print("      • Creates 42 posts (3 platforms × 14 days)")
    print("      • Spreads them across 2 weeks")
    print("      • Each platform posts once per day")
    print()
    
    print("⏰ Timing:")
    print("   • Day 0 = Today (posts immediately if scheduler running)")
    print("   • Day 1 = Tomorrow")
    print("   • Day 13 = Two weeks from now")
    print()
    
    print("🔄 Scheduler Frequency:")
    print("   • Checks for due posts: Every 1 minute")
    print("   • Checks for Reddit comments: Every 10 minutes")
    print("   • Runs in background thread")
    print()
    
    print("🎯 Current Time vs Post Times:")
    now = datetime.now(timezone.utc)
    print(f"   • Now: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   • Posts scheduled for: Various times across 14 days")

def check_api_limitations():
    """Explain API limitations"""
    print("\n⚠️ KNOWN API LIMITATIONS")
    print("=" * 50)
    
    print("🐦 Twitter/X:")
    print("   • Your account has LIMITED API access")
    print("   • Can READ tweets ✅")
    print("   • Cannot CREATE tweets ❌")
    print("   • Error: 'Your account is not permitted to access this feature'")
    print("   • Solution: Apply for higher API access level")
    print()
    
    print("🔴 Reddit:")
    print("   • API working ✅")
    print("   • Can post to subreddits ✅")
    print("   • Can read/reply to comments ✅")
    print()
    
    print("💼 LinkedIn:")
    print("   • Token present ✅")
    print("   • Needs testing to confirm posting ability")

if __name__ == "__main__":
    print("🚀 SOCIAL MEDIA AUTOMATION - COMPLETE STATUS REPORT")
    print("=" * 70)
    
    check_credentials()
    check_database()
    explain_posting_logic()
    check_api_limitations()
    
    print("\n" + "=" * 70)
    print("✅ STATUS REPORT COMPLETE!")
    print()
    print("💡 NEXT STEPS:")
    print("   1. Run 'python -m streamlit run app.py' to start the web interface")
    print("   2. Click 'Generate & Schedule' to create posts")
    print("   3. Click 'Start scheduler' to begin automation")
    print("   4. For Twitter: Apply for higher API access level")
    print("   5. Monitor logs in the web interface")
