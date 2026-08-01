"""
Real Madrid News Bot — AI News Summarizer
Uses Gemini API for AI summaries + deep-translator for Persian translation.
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
    if not news_items:
        return ""

    if GEMINI_API_KEY:
        result = _gemini_summarize(news_items)
        if result:
            return result

    return _translated_template_summary(news_items)


def _gemini_summarize(news_items: list[dict]) -> str:
    news_text = "\n".join(
        f"- {item['title']} (Source: {item.get('source_name', 'Unknown')})"
        for item in news_items
    )

    prompt = f"""تو یک خبرنگار فارسی زبان حرفه ای هستی که برای باشگاه رئال مادرید خبر تهیه می کنی.

این اخبار رئال مادرید رو بخون و یه خلاصه زیبا و یکپارچه به فارسی بنویس.

قوانین:
1. عنوان خبر رو با ایموجی و بولد بنویس
2. زیر هر عنوان، ۲-۳ جمله خلاصه به فارسی بنویس
3. اخبار مرتبط رو با هم ترکیب کن
4. منابع رو در انتهای پیام ذکر کن
5. حداکثر ۵ بخش خبری داشته باش
6. بین بخش‌ها خط جداکننده بذار
7. جذاب و حرفه‌ای بنویس

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
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return text
    except (URLError, TimeoutError, KeyError, IndexError) as e:
        print(f"[WARN] Gemini API failed: {e}, falling back to translated template")
        return ""


def _translated_template_summary(news_items: list[dict]) -> str:
    """Template-based summary with full Persian translation. No duplicate descriptions."""
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
    date_str = tehran_time.strftime("%H:%M — %d %B %Y")
    for en, fa in zip(english_months, jalali_months):
        date_str = date_str.replace(en, fa)

    persian_weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    weekday = persian_weekdays[tehran_time.weekday()]

    lines = [
        "⚽ **خبرنامه رئال مادرید**",
        f"📅 {weekday} — {date_str}",
        "",
    ]

    # Deduplicate: skip if title is too similar to previous
    seen_titles = set()

    for i, item in enumerate(news_items[:5], 1):
        emoji = ["🔵", "🟢", "⚪", "🔴", "🟡"][i - 1]
        source = item.get("source_name", "")

        # Translate title
        original_title = item["title"]
        persian_title = _translate_text(original_title)

        # Dedup: normalize and check similarity
        normalized = re.sub(r"[^a-zA-Z0-9]", "", original_title.lower())
        if normalized in seen_titles:
            continue
        seen_titles.add(normalized)

        lines.append(f"{emoji} **{persian_title}**")

        # Only add description if it's meaningfully different from title
        if item.get("description"):
            desc_lower = re.sub(r"[^a-zA-Z0-9]", "", item["description"].lower())
            title_lower = re.sub(r"[^a-zA-Z0-9]", "", original_title.lower())
            # Skip if description is just the title repeated or very similar
            if desc_lower != title_lower and not desc_lower.startswith(title_lower[:40]):
                desc = _translate_text(item["description"][:200])
                lines.append(f"_{desc}_")

        if source:
            lines.append(f"📎 {source}")

        lines.append("")
        lines.append("ـــــــــــــــــــــــــــــــ")

    # Sources
    sources = list(set(
        item.get("source_name", "") for item in news_items[:5]
        if item.get("source_name")
    ))
    lines.append(f"📎 **منابع:** {' — '.join(sources)}")

    return "\n".join(lines)


if __name__ == "__main__":
    from news_fetcher import get_new_news
    from config import RSS_FEEDS

    print("🔍 در حال دریافت اخبار...")
    news = get_new_news(RSS_FEEDS, 5)
    if news:
        print("\n📝 در حال ساخت خلاصه فارسی...\n")
        summary = summarize_news_persian(news)
        print(summary)
    else:
        print("📭 خبری یافت نشد")
