"""
Real Madrid News Bot — Configuration
"""
import os

# Bot Settings
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# RSS Feed Sources (filtered for Real Madrid)
RSS_FEEDS = [
    {
        "name": "Google News",
        "url": "https://news.google.com/rss/search?q=Real+Madrid+CF&hl=en-US&gl=US&ceid=US:en",
        "filter": "real madrid",
    },
    {
        "name": "Google News (Transfer)",
        "url": "https://news.google.com/rss/search?q=Real+Madrid+transfer+signing&hl=en-US&gl=US&ceid=US:en",
        "filter": "real madrid",
    },
    {
        "name": "BBC Sport Football",
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "filter": "real madrid",
    },
    {
        "name": "Marca Real Madrid",
        "url": "https://www.marca.com/rss/futbol/real-madrid.xml",
        "filter": "",
    },
]

# Telegram Channel Source
TELEGRAM_SOURCES = [
    {
        "name": "@Realmadridfarsi",
        "url": "https://t.me/s/Realmadridfarsi",
    },
]

# News Settings
MAX_NEWS_PER_UPDATE = 30         # Max news items per update (may split into 3 msgs)
MAX_MESSAGES_PER_SEND = 3        # Max messages per update
NEWS_FETCH_INTERVAL_HOURS = 3    # How often to fetch news (hours)
DEDUP_WINDOW_HOURS = 24          # Don't re-send news from last 24h

# Bot Messages (Persian + English)
WELCOME_MSG = """⚽ **Real Madrid News Bot**

به ربات اخبار رئال مادرید خوش اومدی!

📋 دستورات:
/start — شروع مجد
/news — دریافت آخرین اخبار
/players — لیست بازیکنان
/status — وضعیت ربات
/sources — منابع خبری

🔔 اخبار هر ۳ ساعت خودکار ارسال میشه."""

STATUS_MSG = """📊 **وضعیت ربات**

⏰ آخرین بررسی: {last_check}
📰 اخبار ارسال شده: {news_count}
🔄 بازه بروزرسانی: هر {interval} ساعت
✅ وضعیت: فعال"""

SOURCES_MSG = """📰 **منابع خبری:**

1️⃣ **Google News** — اخبار لحظه‌ای رئال مادرید
2️⃣ **Google News Transfer** — نقل و انتقالات
3️⃣ **BBC Sport** — اخبار فوتبال انگلیس و جهان
4️⃣ **Marca** — منبع اسپانیایی رئال مادرید
5️⃣ **@Realmadridfarsi** — کانال فارسی رئال مادرید

🌐 همه منابع از ایران قابل دسترسی هستند."""