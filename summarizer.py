"""
Real Madrid News Bot — AI News Summarizer
Creates cohesive Persian news summaries with auto language detection.
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from urllib.error import URLError

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Lazy-load translators
_translator_en = None
_translator_es = None
_translator_auto = None


def _get_translator(source_lang: str = "auto"):
    """Get or create the appropriate translator."""
    global _translator_en, _translator_es, _translator_auto
    
    if source_lang == "en":
        if _translator_en is None:
            try:
                from deep_translator import GoogleTranslator
                _translator_en = GoogleTranslator(source="en", target="fa")
            except ImportError:
                _translator_en = False
        return _translator_en
    elif source_lang == "es":
        if _translator_es is None:
            try:
                from deep_translator import GoogleTranslator
                _translator_es = GoogleTranslator(source="es", target="fa")
            except ImportError:
                _translator_es = False
        return _translator_es
    else:  # auto
        if _translator_auto is None:
            try:
                from deep_translator import GoogleTranslator
                _translator_auto = GoogleTranslator(source="auto", target="fa")
            except ImportError:
                _translator_auto = False
        return _translator_auto


def _detect_language(text: str) -> str:
    """Detect if text is English or Spanish."""
    # Common Spanish characters and words
    spanish_chars = set("áéíóúñ¿¡")
    spanish_words = ["el", "la", "los", "las", "de", "del", "en", "que", "por", "con", "una", "uno", "es", "se", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "este", "sí", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí", "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros", "mi", "mis", "tú", "te", "ti", "tu", "tus", "ellas", "nosotras", "vosotros", "vosotras", "os", "mío", "mía", "míos", "mías", "tuyo", "tuya", "tuyos", "tuyas", "suyo", "suya", "suyos", "suyas", "nuestro", "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras", "esos", "esas", "estoy", "estás", "está", "estamos", "estáis", "están", "esté", "estés", "estemos", "estéis", "estén", "estaré", "estarás", "estará", "estaremos", "estaréis", "estarán", "estaría", "estarías", "estaríamos", "estaríais", "estarían", "estaba", "estabas", "estábamos", "estabais", "estaban", "estuve", "estuviste", "estuvo", "estuvimos", "estuvisteis", "estuvieron", "estuviera", "estuvieras", "estuviéramos", "estuvierais", "estuvieran", "estuviese", "estuvieses", "estuviésemos", "estuvieseis", "estuviesen", "estando", "estado", "estada", "estados", "estadas", "estad", "he", "has", "ha", "hemos", "habéis", "han", "haya", "hayas", "hayamos", "hayáis", "hayan", "habré", "habrás", "habrá", "habremos", "habréis", "habrán", "habría", "habrías", "habríamos", "habríais", "habrían", "había", "habías", "habíamos", "habíais", "habían", "hube", "hubiste", "hubo", "hubimos", "hubisteis", "hubieron", "hubiera", "hubieras", "hubiéramos", "hubierais", "hubieran", "hubiese", "hubieses", "hubiésemos", "hubieseis", "hubiesen", "habiendo", "habido", "habida", "habidos", "habidas", "soy", "eres", "es", "somos", "sois", "son", "sea", "seas", "seamos", "seáis", "sean", "seré", "serás", "será", "seremos", "seréis", "serán", "sería", "serías", "seríamos", "seríais", "serían", "era", "eras", "éramos", "erais", "eran", "fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron", "fuera", "fueras", "fuéramos", "fuerais", "fueran", "fuese", "fueses", "fuésemos", "fueseis", "fuesen", "siendo", "tenido", "tenida", "tenidos", "tenidas", "tened", "tengo", "tienes", "tiene", "tenemos", "tenéis", "tienen", "tenga", "tengas", "tengamos", "tengáis", "tengan", "tendré", "tendrás", "tendrá", "tendremos", "tendréis", "tendrán", "tendría", "tendrías", "tendríamos", "tendríais", "tendrían", "tenía", "tenías", "teníamos", "teníais", "tenían", "tuve", "tuviste", "tuvo", "tuvimos", "tuvisteis", "tuvieron", "tuviera", "tuvieras", "tuviéramos", "tuvierais", "tuvieran", "tuviese", "tuvieses", "tuviésemos", "tuvieseis", "tuviesen", "teniendo", "tenido", "tenida", "tenidos", "tenidas", "puedo", "puedes", "puede", "podemos", "podéis", "pueden", "pueda", "puedas", "podamos", "podáis", "puedan", "podré", "podrás", "podrá", "podremos", "podréis", "podrán", "podría", "podrías", "podríamos", "podríais", "podrían", "podía", "podías", "podíamos", "podíais", "podían", "pude", "pudiste", "pudo", "pudimos", "pudisteis", "pudieron", "pudiera", "pudieras", "pudiéramos", "pudierais", "pudieran", "pudiese", "pudieses", "pudiésemos", "pudieseis", "pudiesen", "pudiendo", "podido"]
    
    text_lower = text.lower()
    
    # Check for Spanish-specific characters
    if any(c in text_lower for c in spanish_chars):
        return "es"
    
    # Check for Spanish words
    words = set(text_lower.split())
    spanish_matches = len(words.intersection(set(spanish_words)))
    if spanish_matches >= 2:
        return "es"
    
    return "en"


def _translate_text(text: str) -> str:
    """Translate text to Persian with auto language detection."""
    if not text:
        return ""
    
    # Detect language
    lang = _detect_language(text)
    translator = _get_translator(lang)
    
    if translator is False:
        return text
    
    try:
        if len(text) > 4500:
            text = text[:4500]
        return translator.translate(text)
    except Exception as e:
        print(f"[WARN] Translation failed ({lang} -> fa): {e}")
        # Try auto-detect as fallback
        try:
            auto_translator = _get_translator("auto")
            if auto_translator and auto_translator is not False:
                return auto_translator.translate(text)
        except Exception:
            pass
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
    """Create multiple cohesive Persian messages from news items."""
    if not news_items:
        return []

    messages = []
    for i in range(0, len(news_items), max_per_msg):
        chunk = news_items[i:i + max_per_msg]
        msg = summarize_news_persian(chunk)
        if msg:
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

 Rules:
1. یه پیام واحد و منسجم بنویس (نه لیست جداگانه)
2. اخبار مرتبط رو با هم ترکیب کن
3. عنوان اصلی با ایموجی ⚪ بذار
4. زیرش یه پاراگراف خلاصه بنویس که همه اخبار رو پوشش بده
5. منابع رو انتها
6. حداکثر ۳-۴ پاراگراف باشه
7. جذاب و خوانا بنویس

inbox:
{news_text}

الان یه پیام خبری منسجم فارسی بنویس:"""

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

    # Retry with exponential backoff for transient errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                # Handle API error response
                if "error" in data:
                    err = data["error"]
                    code = err.get("code", 0)
                    msg = err.get("message", "Unknown error")
                    if code == 429:  # Rate limit
                        wait = 2 ** attempt
                        print(f"[WARN] Gemini rate limited, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(wait)
                        continue
                    print(f"[WARN] Gemini API error ({code}): {msg}")
                    return ""
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                return text
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt
                print(f"[WARN] Gemini rate limited (HTTP 429), retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            print(f"[WARN] Gemini HTTP error {e.code}: {e.reason}")
            return ""
        except (URLError, TimeoutError, KeyError, IndexError) as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[WARN] Gemini request failed: {e}, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            print(f"[WARN] Gemini API failed after {max_retries} attempts: {e}, falling back to template")
            return ""

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

    # Translate all titles with auto language detection
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
        p1_titles = [item["title_fa"] for item in unique_items[:3]]
        lines.append("🔹 " + " | ".join(p1_titles))
        lines.append("")

        if len(unique_items) > 3:
            p2_titles = [item["title_fa"] for item in unique_items[3:6]]
            lines.append("🔸 " + " | ".join(p2_titles))
            lines.append("")

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
