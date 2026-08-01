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
    prompt = f"""تو یک خبرنگار فارسی زبان حرفه ای هستی که برای باشگاه رئال مادرید خبر تهیه می کنی.

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


# ─── Persian Translations ──────────────────────────────────────
PERSIAN_TRANSLATIONS = {
    # Players
    "vinicius": "وینیسیوس",
    "bellingham": "بلینگام",
    "mbappe": "امباپه",
    "mbappé": "امباپه",
    "modric": "موریچ",
    "kroos": "کروس",
    "courtois": "کورتوا",
    "alaba": "آلابا",
    "carvajal": "کارواخال",
    "mendy": "مندی",
    "valverde": "والورده",
    "rodrygo": "رودریگو",
    "tchouameni": "چوامنی",
    "camavinga": "کاماوینگا",
    "jude": "جود",
    "vinícius": "وینیسیوس",
    "joselu": "خوسلو",
    "luka": "لوکا",
    "dani": "دانی",
    "federico": "فردریکو",
    "eduardo": "ادواردو",
    "thibaut": "تیبوت",
    "antonio": "آنتونیو",
    "aurelien": "اورلین",
    "jacob": "جیکوب",
    "güler": "گولر",
    "arda": "آردا",
    # Clubs
    "real madrid": "رئال مادرید",
    "realmadrid": "رئال مادرید",
    "los blancos": "لوس بلانکوس",
    "madrid": "مادرید",
    "barcelona": "بارسلونا",
    "atletico": "اتلتیکو",
    "champions league": "لیگ قهرمانان",
    "la liga": "لالیگا",
    "laliga": "لالیگا",
    "copa del rey": "جام حذفی",
    "europa league": "لیگ اروپا",
    # Common football terms
    "transfer": "انتقال",
    "signing": "جذب بازیکن",
    "goal": "گل",
    "match": "بازی",
    "victory": "پیروزی",
    "defeat": "شکست",
    "draw": "تساوی",
    "coach": "مربی",
    "manager": "مربی",
    "stadium": "ورزشگاه",
    "santiago bernabeu": "سانتیاگو برنابئو",
    "bernabeu": "برنابئو",
    "injury": "مصدومیت",
    "contract": "قرارداد",
    "renewal": "تمدید",
    "extension": "تمدید",
    "release clause": "بند آزادسازی",
    "buyout": "بند آزادسازی",
    "training": "تمرین",
    "season": "فصل",
    "league": "لیگ",
    "cup": "جام",
    "trophy": "جام",
    "final": "فینال",
    "semifinal": "نیمه نهایی",
    "quarterfinal": "یک چهارم نهایی",
    "score": "نتیجه",
    "result": "نتیجه",
    "starting": "ترکیب اصلی",
    "lineup": "ترکیب",
    "substitution": "تعویض",
    "penalty": "پنالتی",
    "red card": "کارت قرمز",
    "yellow card": "کارت زرد",
    "var": "VAR",
    "world cup": "جام جهانی",
    "preseason": "پیش فصل",
    "pre-season": "پیش فصل",
    "friendly": "دوستانه",
    "stadium": "ورزشگاه",
    "fan": "هوادار",
    "fans": "هواداران",
    "madridista": "مادریدیستا",
}


def _translate_to_persian(title: str) -> str:
    """Translate common football terms in title to Persian."""
    result = title
    # Sort by length (longest first) to avoid partial replacements
    sorted_terms = sorted(PERSIAN_TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True)
    for eng, fa in sorted_terms:
        # Case-insensitive replacement
        import re
        pattern = re.compile(re.escape(eng), re.IGNORECASE)
        result = pattern.sub(fa, result)
    return result


def _template_summary(news_items: list[dict]) -> str:
    """Fallback: template-based Persian summary (no AI needed)."""
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

    # Persian day names
    persian_weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    weekday = persian_weekdays[tehran_time.weekday()]

    lines = [
        "⚽ **خبرنامه رئال مادرید**",
        f"📅 {weekday} — {date_str}",
        "",
    ]

    for i, item in enumerate(news_items[:5], 1):
        emoji = ["🔵", "🟢", "⚪", "🔴", "🟡"][i - 1] if i <= 5 else "⚽"
        source = item.get("source_name", "")

        # Translate title to Persian
        original_title = item["title"]
        persian_title = _translate_to_persian(original_title)

        lines.append(f"{emoji} **{persian_title}**")

        if item.get("description"):
            desc = _translate_to_persian(item["description"][:150])
            lines.append(f"_{desc}_")

        lines.append("")
        lines.append("ـــــــــــــــــــــــــــــــ")

    # Sources
    sources = list(set(item.get("source_name", "") for item in news_items[:5] if item.get("source_name")))
    lines.append(f"📎 **منابع:** {' — '.join(sources)}")

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
