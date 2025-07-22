 # app.py  – 2-week auto-campaign + comment hunter
import os, json, time, sqlite3, schedule, threading, requests
from datetime import datetime, timedelta
from openai import OpenAI
import tweepy, praw
import streamlit as st

# --------------------------------------------------
# 0.  ENV / SECRETS  (never commit to git)
# --------------------------------------------------
from dotenv import load_dotenv
import pathlib
# Load .env from .streamlit if present
dotenv_path = pathlib.Path(__file__).parent / ".." / ".streamlit" / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Only use os.getenv for all posting keys
GROQ_KEY        = os.getenv("GROQ_KEY") or os.getenv("GROQAPI_KEY")
OPENROUTER_KEY  = os.getenv("OPENROUTER_KEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
TW_API_KEY      = os.getenv("TW_API_KEY")
TW_API_SECRET   = os.getenv("TW_API_SECRET")
TW_ACCESS       = os.getenv("TW_ACCESS")
TW_ACCESS_SECRET= os.getenv("TW_ACCESS_SECRET")
TW_BEARER       = os.getenv("TW_BEARER")
CLIENT_ID       = os.getenv("CLIENT_ID")
CLIENT_SECRET   = os.getenv("CLIENT_SECRET")
REDDIT_CLIENT   = os.getenv("REDDIT_CLIENT")
REDDIT_SECRET   = os.getenv("REDDIT_SECRET")
REDDIT_USER     = os.getenv("REDDIT_USER")
REDDIT_PW       = os.getenv("REDDIT_PW")
REDDIT_UA       = os.getenv("REDDIT_UA")
LINKEDIN_CLIENT = os.getenv("LINKEDIN_CLIENT")
LINKEDIN_SECRET = os.getenv("LINKEDIN_SECRET")
LINKEDIN_TOKEN  = os.getenv("LINKEDIN_TOKEN")
WHATSAPP_TOKEN  = os.getenv("WHATSAPP_TOKEN")
PRODUCT_URL     = os.getenv("PRODUCT_URL", "https://bit.ly/qorganizer")

DB_FILE = "campaign.db"

# Ensure table exists at startup using helper function
def init_database():
    """Initialize database with proper error handling"""
    try:
        execute_db_query("""
        CREATE TABLE IF NOT EXISTS posts(
            id TEXT PRIMARY KEY,
            platform TEXT,
            text TEXT,
            scheduled TEXT,
            posted INTEGER DEFAULT 0,
            permalink TEXT
        )""")
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# Initialize database
init_database()

db_lock = threading.Lock()

# --------------------------------------------------
# DATABASE HELPER FUNCTIONS
# --------------------------------------------------
def get_db_connection():
    """Get a database connection with proper timeout and WAL mode"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=memory")
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB
    return conn

def execute_db_query(query, params=None, fetch=False):
    """Execute database query with proper locking and error handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with db_lock:
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    if fetch:
                        result = cursor.fetchall()
                    else:
                        result = None
                    
                    conn.commit()
                    return result
                finally:
                    conn.close()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  # Progressive backoff
                continue
            else:
                raise e
    return None

# --------------------------------------------------
# 1.  GROQ LLM
# --------------------------------------------------
# client = OpenAI(
#     base_url="https://api.groq.com/openai/v1",
#     api_key=GROQ_KEY
# )

# -------------------- LLM Fallback Logic --------------------
FALLBACK_MODELS = [
    # Compound models (Groq, rate-limited, not paywalled)
    "compound-beta-kimi",
    "compound-beta-mini",
    "compound-beta",
    # Fastest, direct Groq API models
    "gemma-7b-it",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "mistral-7b-instruct",
    "llama-3.1-8b-instant"
]

def smart_chat(prompt, max_tokens=120):
    # Try Groq API for all supported models
    if GROQ_KEY:
        for model in FALLBACK_MODELS:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens
                    },
                    timeout=15
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"].strip()
            except Exception:
                continue
    # Try OpenRouter free models
    if OPENROUTER_KEY:
        for model in [
            "google/gemma-2-9b-it:free",
            "google/gemini-1.5-flash-latest:free",
            "moonshotai/kimi-k2:free",
            "mistralai/mistral-7b-instruct:free"
        ]:
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_KEY}",
                        "HTTP-Referer": "https://kamandalabs.me"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens
                    },
                    timeout=15
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"].strip()
            except Exception:
                continue
    # Fallback to Gemini API if available
    if GEMINI_API_KEY:
        try:
            gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            r = requests.post(
                gemini_url + f"?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens}
                },
                timeout=15
            )
st.title("🤖 Auto-Campaign for QuickOrganizer")
if st.button("Generate & Schedule"):
    try:
        plan = get_plan()
        for p in plan:
            text = smart_chat(p["prompt"] + f"\nEnd with link: {PRODUCT_URL}", max_tokens=120)
            if not text: 
                continue
            scheduled = (datetime.utcnow() + timedelta(days=p["day"])).isoformat(timespec="minutes")
            post_id = f"{p['platform']}_{p['day']}"
            
            # Use the new database helper function
            execute_db_query(
                "INSERT OR IGNORE INTO posts VALUES(?,?,?,?,0,'')",
                (post_id, p["platform"], text, scheduled)
            )
        st.success("Posts queued!")
    except Exception as e:
        st.error(f"Error generating posts: {e}")
        add_log(f"Error generating posts: {e}")

try:
    df = execute_db_query("SELECT id,platform,text,scheduled,posted FROM posts ORDER BY scheduled", fetch=True)
    if df:
        st.dataframe(df)
    else:
        st.info("No posts scheduled yet.")
except Exception as e:
    st.error(f"Error loading posts: {e}")
    add_log(f"Error loading posts: {e}")nt=REDDIT_UA
    )

# --------------------------------------------------
# 3.  2-WEEK CALENDAR (EXTENSIBLE)
# --------------------------------------------------
def poster():
    try:
        now = datetime.utcnow().isoformat(timespec="minutes")
        rows = execute_db_query("SELECT * FROM posts WHERE scheduled <= ? AND posted=0", (now,), fetch=True)
        
        if not rows:
            st.session_state["last_posted"] = "No scheduled posts to send right now."
            return
            
        posted_platforms = set()
        for r in rows:
            id_, plat, txt, _, _, _ = r
            try:
                if plat == "x":
                    api = twitter_client()
                    tweet = api.update_status(txt)
                    execute_db_query(
                        "UPDATE posts SET posted=1, permalink=? WHERE id=?", 
                        (f"https://twitter.com/i/web/status/{tweet.id}", id_)
                    )
                    posted_platforms.add("X (Twitter)")
                    add_log(f"Posted to X: {tweet.id}")
                    
                elif plat == "reddit":
                    reddit = reddit_client()
                    sub = next((p.get("sub") for p in get_plan() if f"{p['platform']}_{p['day']}" == id_), None)
                    if sub:
                        post = reddit.subreddit(sub).submit(title=txt[:100], selftext=txt)
                        execute_db_query(
                            "UPDATE posts SET posted=1, permalink=? WHERE id=?", 
                            (post.url, id_)
                        )
                        posted_platforms.add(f"Reddit (r/{sub})")
                        add_log(f"Posted to Reddit r/{sub}: {post.url}")
                        
                elif plat == "linkedin":
                    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}", "Content-Type": "application/json"}
                    payload = {"author": "urn:li:person:me", "lifecycleState": "PUBLISHED",
                               "specificContent": {"com.linkedin.ugc.ShareContent": {
                                   "shareCommentary": {"text": txt}, "shareMediaCategory": "NONE"}},
                               "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}}
                    r = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=payload)
                    if r.status_code == 201:
                        execute_db_query("UPDATE posts SET posted=1 WHERE id=?", (id_,))
                        posted_platforms.add("LinkedIn")
                        add_log(f"Posted to LinkedIn: {id_}")
                        
            except Exception as e:
                st.error(f"{plat} error: {e}")
                add_log(f"Error posting to {plat}: {e}")
def comment_replier():
    try:
        reddit = reddit_client()
        for post in reddit.user.me().submissions.new(limit=10):
            for comment in post.comments:
                if comment.author and comment.author.name != REDDIT_USER and PRODUCT_URL not in comment.body:
                    reply = smart_chat(f"Reply politely to Reddit comment: {comment.body}\nMention {PRODUCT_URL} in 1 sentence.")
                    if reply:
                        comment.reply(reply)
                        add_log(f"Replied to Reddit comment {comment.id} on post {post.id}")
                    time.sleep(2)  # avoid spam
    except Exception as e:
        add_log(f"Error in comment_replier: {e}")on_state.get('logs', [])
    logs.append(f"[{datetime.utcnow().isoformat(timespec='seconds')}] {message}")
    st.session_state['logs'] = logs[-MAX_LOGS:]

def poster():
    conn_bg = sqlite3.connect(DB_FILE, check_same_thread=False)
    now = datetime.utcnow().isoformat(timespec="minutes")
schedule.every(1).minutes.do(poster)
schedule.every(10).minutes.do(comment_replier)

# Background scheduler thread
def run_scheduler():
    """Run scheduler in background with error handling"""
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            add_log(f"Scheduler error: {e}")
            time.sleep(60)  # Wait longer on error

# Initialize scheduler thread as daemon
if 'scheduler_started' not in st.session_state:
    st.session_state['scheduler_started'] = False

if st.button("Start scheduler"):
    if not st.session_state['scheduler_started']:
        poster()  # Immediately process any due posts
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        st.session_state['scheduler_started'] = True
        st.info("Scheduler started! (runs in background)")
        add_log("Scheduler started successfully")
    else:
        st.info("Scheduler is already running")
                api = twitter_client()
                tweet = api.update_status(txt)
                with db_lock:
                    conn_bg.execute("UPDATE posts SET posted=1, permalink=? WHERE id=?", (f"https://twitter.com/i/web/status/{tweet.id}", id_))
                posted_platforms.add("X (Twitter)")
                add_log(f"Posted to X: {tweet.id}")
            elif plat == "reddit":
                reddit = reddit_client()
                sub = next((p.get("sub") for p in get_plan() if f"{p['platform']}_{p['day']}" == id_), None)
                if sub:
                    post = reddit.subreddit(sub).submit(title=txt[:100], selftext=txt)
                    with db_lock:
                        conn_bg.execute("UPDATE posts SET posted=1, permalink=? WHERE id=?", (post.url, id_))
                    posted_platforms.add(f"Reddit (r/{sub})")
                    add_log(f"Posted to Reddit r/{sub}: {post.url}")
            elif plat == "linkedin":
                headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}", "Content-Type": "application/json"}
                payload = {"author": "urn:li:person:me", "lifecycleState": "PUBLISHED",
                           "specificContent": {"com.linkedin.ugc.ShareContent": {
                               "shareCommentary": {"text": txt}, "shareMediaCategory": "NONE"}},
                           "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}}
                r = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=payload)
                if r.status_code == 201:
                    with db_lock:
                        conn_bg.execute("UPDATE posts SET posted=1 WHERE id=?", (id_,))
                    posted_platforms.add("LinkedIn")
                    add_log(f"Posted to LinkedIn: {id_}")
        except Exception as e:
            st.error(f"{plat} error: {e}")
            add_log(f"Error posting to {plat}: {e}")
    with db_lock:
        conn_bg.commit()
    # Show message in UI after posting
    if posted_platforms:
        st.session_state["last_posted"] = f"✅ Finished posting to: {', '.join(posted_platforms)}"
        add_log(st.session_state["last_posted"])
    else:
        st.session_state["last_posted"] = "No scheduled posts to send right now."
    conn_bg.close()

def comment_replier():
    conn_bg = sqlite3.connect(DB_FILE, check_same_thread=False)
    reddit = reddit_client()
    for post in reddit.user.me().submissions.new(limit=10):
        for comment in post.comments:
            if comment.author and comment.author.name != REDDIT_USER and PRODUCT_URL not in comment.body:
                reply = smart_chat(f"Reply politely to Reddit comment: {comment.body}\nMention {PRODUCT_URL} in 1 sentence.")
                if reply:
                    with db_lock:
                        comment.reply(reply)
                    add_log(f"Replied to Reddit comment {comment.id} on post {post.id}")
                time.sleep(2)  # avoid spam
    conn_bg.close()

schedule.every(1).minutes.do(poster)
schedule.every(10).minutes.do(comment_replier)

if st.button("Start scheduler"):
    poster()  # Immediately process any due posts
    threading.Thread(target=lambda: schedule.run_pending(), daemon=True).start()
    st.info("Scheduler running (check logs)")

# Show last posting summary if available
if "last_posted" in st.session_state:
    st.success(st.session_state["last_posted"])

# Log panel UI
st.markdown("### 📋 Background Log Panel")
if st.button("Refresh logs"):
    pass  # Just triggers rerun
st.text_area("Logs (last 50 actions):", value="\n".join(st.session_state['logs']), height=300)

# --------------------------------------------------
# 6.  PACKAGE FOR OTHERS  (limited-scope keys)
# --------------------------------------------------
# See README.md for usage and safety instructions.
