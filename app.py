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

GROQ_KEY        = os.getenv("GROQ_KEY")
OPENROUTER_KEY  = os.getenv("OPENROUTER_KEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
TW_API_KEY      = os.getenv("TW_API_KEY")
TW_API_SECRET   = os.getenv("TW_API_SECRET")
TW_ACCESS       = os.getenv("TW_ACCESS")
TW_ACCESS_SECRET= os.getenv("TW_ACCESS_SECRET")

REDDIT_CLIENT   = os.getenv("REDDIT_CLIENT")
REDDIT_SECRET   = os.getenv("REDDIT_SECRET")
REDDIT_USER     = os.getenv("REDDIT_USER")
REDDIT_PW       = os.getenv("REDDIT_PW")

LINKEDIN_TOKEN  = os.getenv("LINKEDIN_TOKEN")

PRODUCT_URL     = os.getenv("PRODUCT_URL", "https://bit.ly/qorganizer")

DB_FILE = "campaign.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS posts(
    id TEXT PRIMARY KEY,
    platform TEXT,
    text TEXT,
    scheduled TEXT,
    posted INTEGER DEFAULT 0,
    permalink TEXT
)""")
conn.commit()

db_lock = threading.Lock()

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
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass
    return "⚠️ All free models busy, please retry."

# --------------------------------------------------
# 2.  PLATFORM CLIENTS
# --------------------------------------------------
def twitter_client():
    auth = tweepy.OAuth1UserHandler(TW_API_KEY, TW_API_SECRET, TW_ACCESS, TW_ACCESS_SECRET)
    return tweepy.API(auth)

def reddit_client():
    return praw.Reddit(
        client_id=REDDIT_CLIENT,
        client_secret=REDDIT_SECRET,
        username=REDDIT_USER,
        password=REDDIT_PW,
        user_agent="mr.scrapper"
    )

# --------------------------------------------------
# 3.  2-WEEK CALENDAR (EXTENSIBLE)
# --------------------------------------------------
def get_plan():
    # This could be loaded from a config/db in the future
    platforms = [
        {"platform": "x", "prompt": "Write a catchy 1-sentence tweet about messy downloads"},
        {"platform": "reddit", "prompt": "150-word intro post for r/productivity", "sub": "productivity"},
        {"platform": "linkedin", "prompt": "100-word LinkedIn post for freelancers"}
    ]
    plan = []
    for day in range(14):
        for p in platforms:
            entry = dict(p)
            entry["day"] = day
            plan.append(entry)
    return plan

# --------------------------------------------------
# 4.  UI
# --------------------------------------------------
st.title("🤖 Auto-Campaign for QuickOrganizer")
if st.button("Generate & Schedule"):
    for p in get_plan():
        text = smart_chat(p["prompt"] + f"\nEnd with link: {PRODUCT_URL}", max_tokens=120)
        if not text: continue
        scheduled = (datetime.utcnow() + timedelta(days=p["day"])).isoformat(timespec="minutes")
        post_id = f"{p['platform']}_{p['day']}"
        with db_lock:
            conn.execute("INSERT OR IGNORE INTO posts VALUES(?,?,?,?,0,'')",
                         (post_id, p["platform"], text, scheduled))
    with db_lock:
        conn.commit()
    st.success("Posts queued!")

df = conn.execute("SELECT id,platform,text,scheduled,posted FROM posts ORDER BY scheduled").fetchall()
st.dataframe(df)

# --------------------------------------------------
# 5.  POSTER + COMMENT REPLIER (EXTENSIBLE)
# --------------------------------------------------
# Initialize logs in session state
if 'logs' not in st.session_state:
    st.session_state['logs'] = []

MAX_LOGS = 50  # Number of log entries to keep

def add_log(message):
    logs = st.session_state.get('logs', [])
    logs.append(f"[{datetime.utcnow().isoformat(timespec='seconds')}] {message}")
    st.session_state['logs'] = logs[-MAX_LOGS:]

def poster():
    conn_bg = sqlite3.connect(DB_FILE, check_same_thread=False)
    now = datetime.utcnow().isoformat(timespec="minutes")
    with db_lock:
        rows = conn_bg.execute("SELECT * FROM posts WHERE scheduled <= ? AND posted=0", (now,)).fetchall()
    posted_platforms = set()
    for r in rows:
        id_, plat, txt, _, _, _ = r
        try:
            if plat == "x":
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
"""
HOW OTHER USERS USE IT SAFELY
1. pip install streamlit tweepy praw python-dotenv
2. Copy this file + create .env with ONLY the keys they need
   TW_API_KEY=...
   REDDIT_CLIENT=...
   LINKEDIN_TOKEN=...
3. Run:  streamlit run app.py
4. Keys stay in .env, never committed to git.
5. For extra safety, give them **read-only** Reddit tokens and **Essential** Twitter keys only.
"""
