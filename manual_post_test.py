# manual_post_test.py - Manual posting test
import os
import tweepy
import praw
import requests
from dotenv import load_dotenv
import pathlib
from datetime import datetime, timezone

# Load environment variables
dotenv_path = pathlib.Path(__file__).parent / ".." / ".streamlit" / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"✅ Loaded environment from: {dotenv_path}")

# Credentials
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS = os.getenv("TW_ACCESS")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")
TW_BEARER = os.getenv("TW_BEARER")

REDDIT_CLIENT = os.getenv("REDDIT_CLIENT")
REDDIT_SECRET = os.getenv("REDDIT_SECRET")
REDDIT_USER = os.getenv("REDDIT_USER")
REDDIT_PW = os.getenv("REDDIT_PW")
REDDIT_UA = os.getenv("REDDIT_UA")

LINKEDIN_TOKEN = os.getenv("LINKEDIN_TOKEN")
PRODUCT_URL = os.getenv("PRODUCT_URL", "https://bit.ly/qorganizer")

def check_twitter_permissions():
    """Check what Twitter API permissions we have"""
    print("🔍 Checking Twitter API Permissions...")
    try:
        client = tweepy.Client(
            bearer_token=TW_BEARER,
            consumer_key=TW_API_KEY,
            consumer_secret=TW_API_SECRET,
            access_token=TW_ACCESS,
            access_token_secret=TW_ACCESS_SECRET
        )
        
        # Test read access
        user = client.get_me()
        print(f"✅ Can read account info: @{user.data.username}")
        
        # Test write access
        try:
            test_text = f"🧪 API Test - {datetime.now(timezone.utc).strftime('%H:%M:%S')}"
            response = client.create_tweet(text=test_text)
            print(f"✅ Can create tweets: Tweet ID {response.data['id']}")
            return True
        except Exception as write_error:
            print(f"❌ Cannot create tweets: {write_error}")
            print("💡 Your Twitter API access level only allows reading, not posting")
            return False
            
    except Exception as e:
        print(f"❌ Twitter connection error: {e}")
        return False

def test_twitter_post():
    """Test posting to Twitter"""
    print("🐦 Testing Twitter Post...")
    
    if not check_twitter_permissions():
        print("⚠️ Skipping Twitter posting due to API limitations")
        return False
    
    try:
        client = tweepy.Client(
            bearer_token=TW_BEARER,
            consumer_key=TW_API_KEY,
            consumer_secret=TW_API_SECRET,
            access_token=TW_ACCESS,
            access_token_secret=TW_ACCESS_SECRET,
            wait_on_rate_limit=True
        )
        
        test_text = f"🧪 Testing automated posting from QuickOrganizer campaign at {datetime.now(timezone.utc).strftime('%H:%M')} - {PRODUCT_URL}"
        
        response = client.create_tweet(text=test_text)
        tweet_id = response.data['id']
        
        print(f"✅ Twitter post successful!")
        print(f"   Tweet ID: {tweet_id}")
        print(f"   URL: https://twitter.com/i/web/status/{tweet_id}")
        print(f"   Text: {test_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Twitter error: {e}")
        return False

def test_reddit_post():
    """Test posting to Reddit"""
    print("🔴 Testing Reddit Post...")
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT,
            client_secret=REDDIT_SECRET,
            username=REDDIT_USER,
            password=REDDIT_PW,
            user_agent=REDDIT_UA
        )
        
        title = f"🧪 Testing Productivity Tool - QuickOrganizer"
        text = f"""Just testing our new productivity automation tool!

**QuickOrganizer** helps you declutter your downloads and organize files automatically.

🎯 Key features:
- Automatic file organization
- No installation required  
- Works with any file type
- Free to use

Check it out: {PRODUCT_URL}

*Posted via automation at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}*"""

        # Test with a safe subreddit (your own profile)
        subreddit = reddit.subreddit("test")  # r/test is for testing
        
        post = subreddit.submit(title=title, selftext=text)
        
        print(f"✅ Reddit post successful!")
        print(f"   Post ID: {post.id}")
        print(f"   URL: {post.url}")
        print(f"   Subreddit: r/{post.subreddit}")
        print(f"   Title: {title}")
        
        return True
        
    except Exception as e:
        print(f"❌ Reddit error: {e}")
        print("💡 Tip: Make sure your account has enough karma and isn't rate limited")
        return False

def test_linkedin_post():
    """Test posting to LinkedIn"""
    print("💼 Testing LinkedIn Post...")
    
    if not LINKEDIN_TOKEN:
        print("❌ LinkedIn token not found")
        return False
    
    try:
        headers = {
            "Authorization": f"Bearer {LINKEDIN_TOKEN}",
            "Content-Type": "application/json"
        }
        
        test_text = f"""🧪 Testing LinkedIn automation from QuickOrganizer!

📁 Tired of messy downloads? Our tool helps you organize files automatically.

🎯 Features:
• Automatic file sorting
• No installation required
• Works with any file type
• Completely free

Try it out: {PRODUCT_URL}

#Productivity #FileManagement #Organization
Posted via automation at {datetime.now(timezone.utc).strftime('%H:%M')}"""
        
        payload = {
            "author": "urn:li:person:me",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": test_text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            print(f"✅ LinkedIn post successful!")
            print(f"   Response: {response.status_code}")
            print(f"   Text preview: {test_text[:100]}...")
            return True
        else:
            print(f"❌ LinkedIn error: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ LinkedIn error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 MANUAL POSTING TEST")
    print("=" * 60)
    
    choice = input("Test (1) Twitter, (2) Reddit, (3) LinkedIn, or (4) All? [1/2/3/4]: ").strip()
    
    if choice in ['1', '4']:
        test_twitter_post()
        print()
    
    if choice in ['2', '4']:
        test_reddit_post()
        print()
        
    if choice in ['3', '4']:
        test_linkedin_post()
        print()
    
    print("=" * 60)
    print("✅ Test Complete!")
