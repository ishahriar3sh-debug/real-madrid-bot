"""
Real Madrid News Bot - Configuration
Purple/dark modern theme with expanded news sources.
"""
import os

# ─── Bot Settings ──────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# ─── RSS Feed Sources ──────────────────────────────────────────
RSS_FEEDS = [
    # Match/Result News
    {
        "name": "ESPN FC",
        "url": "https://www.espn.com/espn/rss/soccer/news",
        "filter": "real madrid",
        "category": "match",
    },
    {
        "name": "BBC Sport",
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "filter": "real madrid",
        "category": "match",
    },
    {
        "name": "Sky Sports",
        "url": "https://www.skysports.com/rss/football",
        "filter": "real madrid",
        "category": "match",
    },
    # Transfer News
    {
        "name": "Google News Transfer",
        "url": "https://news.google.com/rss/search?q=Real+Madrid+transfer+signing&hl=en-US&gl=US&ceid=US:en",
        "filter": "real madrid",
        "category": "transfer",
    },
    {
        "name": "Diario AS",
        "url": "https://www.as.com/rss/futbol/real-madrid.xml",
        "filter": "",
        "category": "transfer",
    },
    {
        "name": "Sport EN",
        "url": "https://www.sporten.es/rss/real-madrid.xml",
        "filter": "",
        "category": "transfer",
    },
    # Tactical/Analysis
    {
        "name": "Marca Real Madrid",
        "url": "https://www.marca.com/rss/futbol/real-madrid.xml",
        "filter": "",
        "category": "tactical",
    },
    {
        "name": "Managing Madrid",
        "url": "https://www.managingmadrid.com/rss/feed",
        "filter": "",
        "category": "tactical",
    },
    # General
    {
        "name": "Google News",
        "url": "https://news.google.com/rss/search?q=Real+Madrid+CF&hl=en-US&gl=US&ceid=US:en",
        "filter": "real madrid",
        "category": "general",
    },
]

# ─── Telegram Channel Sources ──────────────────────────────────
TELEGRAM_SOURCES = [
    {
        "name": "@Realmadridfarsi",
        "url": "https://t.me/s/Realmadridfarsi",
        "category": "persian",
    },
]

# ─── News Settings ──────────────────────────────────────────────
MAX_NEWS_PER_UPDATE = 30
MAX_MESSAGES_PER_SEND = 3
NEWS_FETCH_INTERVAL_HOURS = 3
DEDUP_WINDOW_HOURS = 24

# ─── Bot Messages (Purple/Dark Theme) ──────────────────────────
WELCOME_MSG = """purple **ربات اخبار رئال مادرید**

به دنیای اخبار سرخ‌پوش بخوش آمدید! white

**دستورات:**
/news - دریافت آخرین اخبار
/players - لیست بازیکنان
/status - وضعیت رobot
/sources - منابع خبری

bell اخبار هر 3 ساعت خودکار ارسال می‌شود.
━━━━━━━━━━━━━━━━━━━━"""

STATUS_MSG = """stats **وضعیت ربات**

last آخرین بررسی: {last_check}
paper تعداد اخبار: {news_count}
cycle بازه بروزرسانی: هر {interval} ساعت
check وضعیت: فعال
━━━━━━━━━━━━━━━━━━━━"""

SOURCES_MSG = """paper **منابع خبری**

white **منابع:**
1. ESPN FC - اخبار لحظه‌ای
2. BBC Sport - اخبار فوتبال جهان
3. Sky Sports - اخبار فوتبال انگلیس
4. Diario AS - روزنامه اسپانیایی
5. Sport EN - اخبار ویژه رئال مادرید
6. Marca - منبع تخصصی رئال مادرید
7. Managing Madrid - تحلیل و بررسی فنی
8. Google News - اخبار جمع‌بندی شده
9. @Realmadridfarsi - کانال فارسی رئال مادرید

globe همه منابع از ایران قابل دسترسی هستند.
━━━━━━━━━━━━━━━━━━━━"""

# ─── Category Labels ───────────────────────────────────────────
CATEGORY_LABELS = {
    "match": "soccer **نتیجه و بازی**",
    "transfer": "cycle **انتقالات**",
    "tactical": "brain **تکتیک و تحلیل**",
    "general": "paper **خبر عمومی**",
    "persian": "iran **از کانال فارسی**",
}

# ─── Persian News Category Keywords ────────────────────────────
PERSIAN_NEWS_CATEGORIES = {
    "match": ["نتیجه", "گل", "برد", "باخت", "ترکیب", "لیگ", "قهرمانی"],
    "transfer": ["انتقال", "خرید", "فروش", "اجاره", "بازیکن جدید"],
    "tactical": ["تکتیک", "تحلیل", "بررسی", "عملکرد", "آمار", "استراتژی"],
    "general": ["خبر", "رویداد", "روز"],
}