"""
Real Madrid News Bot — AI News Summarizer
Uses Google Gemini free API to create Persian summaries.
"""
import json
import os
import urllib.request
from urllib.error import URLError

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"  # Free tier model
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def summarize_news_persian(news_items: list[dict]) -> str:
    """
    Use Gemini API to create a beautiful Persian summary of Real Madrid news.
    Falls back to template-based summary if API is unavailable.
    """
    if not news_items:
        return ""

    # Build the news text for AI
    news_text = "\n".join(
        f"- {item['title']} (Source: {item.get('source_name', 'Unknown')})"
        for item in news_items
    )

    if GEMINI_API_KEY:
        return _gemini_summarize(news_text, news_items)
    else:
        return _template_summary(news_items)


def _gemini_summarize(news_text: str, news_items: list[dict]) -> str:
    """Call Gemini API for Persian summary."""
    prompt = f"""تو یک خبرنگار فارسی‌زبان حرفه‌ای هستی که برای باشگاه رئال مادرید خبر تهیه می‌کنی.

این اخبار رئال مادرید رو بخون و یه خلاصه زیبا و یکپارچه به فارسی بنویس.

قوانین:
1. عنوان خبر رو با ایموجی و بولد بنویس (مثل **🔵 عنوان**)
2. زیر هر عنوان، ۲-۳ جمله خلاصه به فارسی بنویس
3. اخبار مرتبط رو با هم ترکیب کن (مثلاً چند خبر انتقالی رو یکجا)
4. منابع رو در انتهای پیام با فرمت «📎 منابع: ...» ذکر کن
5. تاریخ شمسی هم بنویس
6. حداکثر ۵ بخش خبری داشته باش
7. بین بخش‌ها خط جداکننده «ـــــــــــــــــــــــــــــــ» بذار
8. لینک نذار (تو تلگرام اضافه‌ست)
9. جذاب و حرفه‌ای بنویس

اخبار:
{news_text}

حالا خلاصه فارسی رو بنویس:"""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500,
        },
    }).encode()

    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean up markdown formatting
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return text
    except (URLError, TimeoutError, KeyError, IndexError) as e:
        print(f"[WARN] Gemini API failed: {e}, falling back to template")
        return _template_summary(news_items)


def _template_summary(news_items: list[dict]) -> str:
    """Fallback: template-based Persian summary (no AI needed)."""
    from datetime import datetime, timezone, timedelta

    # Persian month names
    jalali_months = [
        "ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
        "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"
    ]
    now = datetime.now(timezone.utc)
    tehran_offset = timedelta(hours=3, minutes=30)
    tehran_time = now + tehran_offset
    date_str = tehran_time.strftime("%H:%M — %d %B %Y")
    for i, m in enumerate(jalali_months):
        date_str = date_str.replace(m, ["ژانویه","فوریه","مارس","آوریل","مه","ژوئن","ژوئیه","اوت","سپتامبر","اکتبر","نوامبر","دسامبر"][i])

    lines = ["⚽ **خبرنامه رئال مادرید**", ""]

    for i, item in enumerate(news_items[:5], 1):
        emoji = ["🔵", "🟢", "⚪", "🔴", "🟡"][i - 1] if i <= 5 else "⚽"
        source = item.get("source_name", "")
        lines.append(f"{emoji} **{item['title']}**")
        if item.get("description"):
            lines.append(f"_{item['description'][:150]}_")
        lines.append("")
        lines.append("ـــــــــــــــــــــــــــــــ")

    # Sources
    sources = list(set(item.get("source_name", "") for item in news_items[:5] if item.get("source_name")))
    lines.append(f"📎 **منابع:** {' — '.join(sources)}")
    lines.append(f"🕐 _{date_str}_")

    return "\n".join(lines)


if __name__ == "__main__":
    """Test the summarizer."""
    from news_fetcher import get_new_news
    from config import RSS_FEEDS

    print("🔍 Fetching news...")
    news = get_new_news(RSS_FEEDS, 5)
    if news:
        print("\n📝 Generating summary...\n")
        summary = summarize_news_persian(news)
        print(summary)
    else:
        print("No news found")
