"""
Real Madrid News Bot — Standalone Cron Script
Fetches news and sends directly to Telegram (no Hermes agent needed).
Run via: python send_news_cron.py

Uses shared modules from the main bot package — no duplicated code.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config import BOT_TOKEN, ADMIN_CHAT_ID, RSS_FEEDS, TELEGRAM_SOURCES
from news_fetcher import get_new_news, MAX_NEWS_PER_UPDATE
from summarizer import summarize_news_multi_persian


def send_telegram(text: str, photo_url: str = None) -> bool:
    """Send message to Telegram via direct API call."""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set!")
        return False

    if photo_url:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "caption": text[:1024],
            "parse_mode": "Markdown",
            "photo": photo_url,
        }
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }

    import urllib.parse
    encoded = urllib.parse.urlencode(data).encode()
    req = Request(url, data=encoded, method="POST")

    try:
        with urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            if result.get("ok"):
                print("✅ Message sent successfully")
                return True
            else:
                print(f"❌ Telegram error: {result}")
                return False
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        return False


def main():
    print(f"[{datetime.now().time()}] 🔍 Fetching Real Madrid news...")

    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
    if not news:
        print("📭 No new news found. Skipping.")
        return

    print(f"📰 Found {len(news)} new items")

    messages = summarize_news_multi_persian(news, max_per_msg=10)
    if not messages:
        print("❌ Failed to build summary")
        return

    # Send with first image if available
    img_url = None
    for item in news:
        if item.get("image_url"):
            img_url = item["image_url"]
            break

    print(f"📤 Sending to Telegram...")
    for i, msg in enumerate(messages):
        photo = img_url if i == 0 else None
        send_telegram(msg, photo)

    print("✅ Done!")


if __name__ == "__main__":
    main()