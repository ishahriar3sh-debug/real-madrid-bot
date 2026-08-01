"""
Real Madrid News Bot — AI News Summarizer
Creates cohesive Persian news summaries, split into multiple messages if needed.
"""
import json
import os
import re
import urllib.request
from urllib.error import URLError

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

_translator = None


def _get_translator():
    global _translator
    if _translator is None:
        try:
            from deep_translator import GoogleTranslator
            _translator = GoogleTranslator(source="en", target="fa")
        except ImportError:
            _translator = False
    return _translator


def _translate_text(text: str) -> str:
    if not text:
        return ""
    translator = _get_translator()
    if translator is False:
        return text
    try:
        if len(text) > 4500:
            text = text[:4500]
        return translator.translate(text)
    except Exception as e:
        print(f"[WARN] Translation failed: {e}")
        return text


def summarize_news_persian(news_items: list[dict]) -> str:
    """Create a single cohesive Persian summary of all Real Madrid news."""
    if not news_items:
        return ""

    if GEMINI_API_KEY:
        result = _gemini_summarize(news_items)
        if result:
            return result

    return _cohesive_persian_summary(news_items)


def summarize_news_multi_persian(news_items: list[dict], max_per_msg: int = 10) -> list[str]:
    """
    Create multiple cohesive Persian messages from news items.
    Splits into chunks of max_per_msg items.
    Returns a list of message strings.
    """
    if not news_items:
        return []

    messages = []
    # Split news into chunks
    for i in range(0, len(news_items), max_per_msg):
        chunk = news_items[i:i + max_per_msg]
        msg = summarize_news_persian(chunk)
        if msg:
            # Add part number if multiple messages
            if len(news_items) > max_per_msg:
                part_num = (i // max_per_msg) + 1
                total_parts = (len(news_items) + max_per_msg - 1) // max_per_msg
                msg = f"📨 **بخش {part_num} از {total_parts}**\n\n{msg}"
            messages.append(msg)

    return messages


def _gemini_summarize(news_items: list[dict]) -> str:
    news_text = "\n".join(
        f"- {item['title']} ({item.get('source_name', 'Unknown')})"
        for item in news_items
    )

    prompt = f"""تو یک خبرنگار حرفه ای فارسی زبان هستی که اخبار رئال مادرید رو پوشش میدی.

این اخبار رو بخون و یه پیام خبری منسجم و یکپارچه به فارسی بنویس.

قوانین:
1. یه پیام واحد و منسجم بنویس (نه لیست جداگانه)
2. اخبار مرتبط رو با هم ترکیب کن
3. عنوان اصلی با ایموجی ⚪ بذار
4. زیرش یه پاراگراف خلاصه بنویس که همه اخبار رو پوشش بده
5. منابع رو انتهای پیام بنویس
6. حداکثر ۳-۴ پاراگراف باشه
7. جذاب و خوانا بنویس

اخبار:
{news_text}

حالا یه پیام خبری منسجم فارسی بنویس:"""

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
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return text
    except (URLError, TimeoutError, KeyError, IndexError) as e:
        print(f"[WARN] Gemini API failed: {e}, falling back to cohesive template")
        return ""


def _cohesive_persian_summary(news_items: list[dict]) -> str:
    """Create a single cohesive Persian message from news items."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    tehran_offset = timedelta(hours=3, minutes=30)
    tehran_time = now + tehran_offset

    # Persian date
    jalali_months = [
        "ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
        "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"
    ]
    english_months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    date_str = tehran_time.strftime("%d %B %Y")
    for en, fa in zip(english_months, jalali_months):
        date_str = date_str.replace(en, fa)

    persian_weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    weekday = persian_weekdays[tehran_time.weekday()]

    # Translate all titles
    translated_items = []
    for item in news_items[:10]:
        title_fa = _translate_text(item["title"])
        translated_items.append({
            "title_en": item["title"],
            "title_fa": title_fa,
            "source": item.get("source_name", ""),
        })

    # Deduplicate
    seen = set()
    unique_items = []
    for item in translated_items:
        key = re.sub(r"[^a-zA-Z0-9]", "", item["title_en"].lower())
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    # Create cohesive message
    lines = [
        f"⚪ **خبرنامه رئال مادرید**",
        f"📅 {weekday} — {date_str}",
        "",
    ]

    # Group into paragraphs
    if len(unique_items) >= 3:
        # Paragraph 1: First 3 items
        p1_titles = [item["title_fa"] for item in unique_items[:3]]
        lines.append("🔹 " + " | ".join(p1_titles))
        lines.append("")

        # Paragraph 2: Next items
        if len(unique_items) > 3:
            p2_titles = [item["title_fa"] for item in unique_items[3:6]]
            lines.append("🔸 " + " | ".join(p2_titles))
            lines.append("")

        # Paragraph 3: Remaining
        if len(unique_items) > 6:
            p3_titles = [item["title_fa"] for item in unique_items[6:9]]
            lines.append("🔹 " + " | ".join(p3_titles))
            lines.append("")
    else:
        for item in unique_items:
            lines.append(f"⚪ {item['title_fa']}")
            lines.append("")

    # Sources
    sources = list(set(item["source"] for item in unique_items if item["source"]))
    if sources:
        lines.append(f"📎 **منابع:** {' — '.join(sources[:3])}")

    return "\n".join(lines)


if __name__ == "__main__":
    from news_fetcher import get_new_news
    from config import RSS_FEEDS, TELEGRAM_SOURCES

    print("🔍 در حال دریافت اخبار...")
    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, 20)
    if news:
        print(f"\n📝 {len(news)} خبر یافت شد. در حال ساخت خلاصه...\n")
        messages = summarize_news_multi_persian(news, max_per_msg=10)
        for i, msg in enumerate(messages, 1):
            print(f"=== پیام {i} ===")
            print(msg)
            print()
    else:
        print("📭 خبری یافت نشد")
