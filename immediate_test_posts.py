# immediate_test_posts.py - Schedule posts for immediate testing
import sqlite3
from datetime import datetime, timezone, timedelta

DB_FILE = "campaign.db"

def schedule_immediate_test_posts():
    """Schedule test posts for the next few minutes"""
    print("⚡ SCHEDULING IMMEDIATE TEST POSTS")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc)
        
        test_posts = [
            {
                "id": "test_reddit_immediate",
                "platform": "reddit", 
                "text": f"🧪 IMMEDIATE TEST: QuickOrganizer helps declutter your downloads! Perfect for productivity enthusiasts who want organized files without the hassle. Try it free: https://bit.ly/qorganizer #productivity #filemanagement",
                "scheduled": (now + timedelta(minutes=1)).isoformat(timespec="minutes")
            },
            {
                "id": "test_linkedin_immediate", 
                "platform": "linkedin",
                "text": f"🚀 Testing LinkedIn automation! QuickOrganizer is a game-changer for file organization. No more messy downloads folder! https://bit.ly/qorganizer #ProductivityTools #FileOrganization",
                "scheduled": (now + timedelta(minutes=3)).isoformat(timespec="minutes")  
            }
        ]
        
        for post in test_posts:
            cursor.execute("""
                INSERT OR REPLACE INTO posts (id, platform, text, scheduled, posted, permalink)
                VALUES (?, ?, ?, ?, 0, '')
            """, (post["id"], post["platform"], post["text"], post["scheduled"]))
            
            print(f"✅ Scheduled {post['platform'].upper()}: {post['scheduled']}")
            print(f"   Text: {post['text'][:60]}...")
            print()
        
        conn.commit()
        conn.close()
        
        print("🎯 SUCCESS!")
        print("💡 Now run your Streamlit app and click 'Start scheduler'")
        print("📋 These posts will be sent in 1-3 minutes")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    schedule_immediate_test_posts()
