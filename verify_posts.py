# verify_posts.py - Manual verification script
import os
import tweepy
import praw
from dotenv import load_dotenv
import pathlib

# Load environment variables from the same location as the main app
dotenv_path = pathlib.Path(__file__).parent / ".." / ".streamlit" / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"✅ Loaded environment from: {dotenv_path}")
else:
    load_dotenv()
    print("⚠️ Loading environment from current directory")

# Twitter credentials
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS = os.getenv("TW_ACCESS")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")
TW_BEARER = os.getenv("TW_BEARER")

# Reddit credentials
REDDIT_CLIENT = os.getenv("REDDIT_CLIENT")
REDDIT_SECRET = os.getenv("REDDIT_SECRET")
REDDIT_USER = os.getenv("REDDIT_USER")
REDDIT_PW = os.getenv("REDDIT_PW")
REDDIT_UA = os.getenv("REDDIT_UA")

def verify_twitter_posts():
    """Check recent Twitter posts"""
    print("🐦 Checking Twitter Posts...")
    try:
        client = tweepy.Client(
            bearer_token=TW_BEARER,
            consumer_key=TW_API_KEY,
            consumer_secret=TW_API_SECRET,
            access_token=TW_ACCESS,
            access_token_secret=TW_ACCESS_SECRET
        )
        
        # Get user's recent tweets
        user = client.get_me()
        print(f"📋 Account: @{user.data.username} ({user.data.name})")
        
        tweets = client.get_users_tweets(user.data.id, max_results=10)
        
        if tweets.data:
            print(f"✅ Found {len(tweets.data)} recent tweets:")
            for i, tweet in enumerate(tweets.data, 1):
                print(f"{i}. Tweet ID: {tweet.id}")
                print(f"   Text: {tweet.text[:100]}...")
                print(f"   URL: https://twitter.com/i/web/status/{tweet.id}")
                print()
        else:
            print("❌ No tweets found")
            
    except Exception as e:
        print(f"❌ Twitter error: {e}")

def verify_reddit_posts():
    """Check recent Reddit posts"""
    print("🔴 Checking Reddit Posts...")
    try:
        print(f"🔍 Debug - Reddit Client ID: {REDDIT_CLIENT[:10]}... (masked)")
        print(f"🔍 Debug - Reddit Username: {REDDIT_USER}")
        
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT,
            client_secret=REDDIT_SECRET,
            username=REDDIT_USER,
            password=REDDIT_PW,
            user_agent=REDDIT_UA
        )
        
        # Test authentication first
        user = reddit.user.me()
        print(f"📋 Reddit User: u/{user.name}")
        
        # Get user's recent submissions
        submissions = list(reddit.user.me().submissions.new(limit=10))
        
        if submissions:
            print(f"✅ Found {len(submissions)} recent posts:")
            for i, post in enumerate(submissions, 1):
                print(f"{i}. Post ID: {post.id}")
                print(f"   Title: {post.title[:80]}...")
                print(f"   Subreddit: r/{post.subreddit}")
                print(f"   URL: {post.url}")
                print(f"   Score: {post.score} | Comments: {post.num_comments}")
                print()
        else:
            print("❌ No posts found")
            
    except Exception as e:
        print(f"❌ Reddit error: {e}")
        print("💡 Tip: Check if your Reddit credentials are correct and account has posting permissions")

def test_api_access():
    """Test API access levels"""
    print("🔐 Testing API Access...")
    
    # Test Twitter API v2 access
    try:
        client = tweepy.Client(bearer_token=TW_BEARER)
        user = client.get_me()
        print(f"✅ Twitter API v2 Read Access: Working")
        print(f"   User: @{user.data.username}")
    except Exception as e:
        print(f"❌ Twitter API v2 Error: {e}")
    
    # Test Reddit API access
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT,
            client_secret=REDDIT_SECRET,
            username=REDDIT_USER,
            password=REDDIT_PW,
            user_agent=REDDIT_UA
        )
        user = reddit.user.me()
        print(f"✅ Reddit API Access: Working")
        print(f"   User: u/{user.name}")
    except Exception as e:
        print(f"❌ Reddit API Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SOCIAL MEDIA POST VERIFICATION")
    print("=" * 60)
    
    test_api_access()
    print()
    verify_twitter_posts()
    print()
    verify_reddit_posts()
    
    print("=" * 60)
    print("✅ Verification Complete!")
