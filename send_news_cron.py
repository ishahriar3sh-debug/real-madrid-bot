"""
Real Madrid News Bot — Standalone Cron Script
Fetches news and sends directly to Telegram (no Hermes agent needed).
Run via: python send_news_cron.py
"""
import json
import os
import sys
import time
import hashlib
import re
import xml.etree.ElementTree as ET
from html import unescape
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import datetime, timezone, timedelta

# ─── Configuration ──────────────────────────────────────────────

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8792366937:AAFQTvY79e5YwOhqdDgB9HZOb8bEEMVF1wM")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "580003433")

RSS_FEEDS = [
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=Real+Madrid+CF&hl=en-US&gl=US&ceid=US:en", "filter": "real madrid"},
    {"name": "Google News Transfer", "url": "https://news.google.com/rss/search?q=Real+Madrid+transfer&hl=en-US&gl=US&ceid=US:en", "filter": "real madrid"},
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "filter": "real madrid"},
    {"name": "Marca Real Madrid", "url": "https://www.marca.com/rss/futbol/real-madrid.xml", "filter": ""},
]

TELEGRAM_SOURCES = [
    {"name": "@Realmadridfarsi", "url": "https://t.me/s/Realmadridfarsi"},
]

NS_MEDIA = {"media": "http://search.yahoo.com/mrss/"}
CACHE_FILE = os.path.join(os.path.dirname(__file__), "seen_news_cron.json")
USER_AGENT = "RealMadridNewsBot/1.0"

# ─── Helper Functions ───────────────────────────────────────────

def clean_html(text):
    if not text: return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()

def news_hash(title):
    return hashlib.md5(re.sub(r"[^a-zA-Z0-9]", "", title.lower()).encode()).hexdigest()

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_cache(cache):
    cutoff = time.time() - 48 * 3600
    cleaned = {k: v for k, v in cache.items() if v > cutoff}
    with open(CACHE_FILE, "w") as f: json.dump(cleaned, f)

def fetch_feed(url):
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=15) as r: return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}")
        return ""

def parse_feed(xml_text):
    items = []
    if not xml_text: return items
    try: root = ET.fromstring(xml_text)
    except: return items
    
    for item in root.findall(".//item"):
        title = clean_html(item.findtext("title", ""))
        link = item.findtext("link", "")
        desc = clean_html(item.findtext("description", ""))[:200]
        pub = item.findtext("pubDate", "")
        source = item.findtext("source", "")
        
        image_url = ""
        media = item.findall("media:content", NS_MEDIA)
        if media: image_url = media[0].get("url", "")
        else:
            enc = item.find("enclosure")
            if enc is not None and "image" in enc.get("type", ""):
                image_url = enc.get("url", "")
        
        if title:
            items.append({"title": title, "link": link, "description": desc, "pub_date": pub, "source": source, "image_url": image_url})
    return items

def fetch_telegram(url):
    items = []
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=15) as r: html = r.read().decode("utf-8", errors="replace")
    except: return []
    
    blocks = re.findall(r'class="tgme_widget_message_wrap[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
    for block in blocks[:20]:
        text_match = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
        if not text_match: continue
        text = clean_html(text_match.group(1))
        if len(text) < 20: continue
        
        img_match = re.search(r'class="tgme_widget_message_photo_wrap"[^>]*style="background-image:url\(&#039;([^&]+)', block)
        image_url = img_match.group(1) if img_match else ""
        
        items.append({"title": text[:150].strip(), "link": url, "description": text[:200], "pub_date": "", "source": "Telegram", "image_url": image_url})
    return items

def get_new_news(max_items=15):
    cache = load_cache()
    all_items = []
    seen = set()
    
    for feed in RSS_FEEDS:
        xml = fetch_feed(feed["url"])
        if not xml: continue
        items = parse_feed(xml)
        flt = feed.get("filter", "real madrid").lower()
        for item in items:
            if flt:
                if flt not in item["title"].lower() and flt not in item.get("description", "").lower(): continue
            h = news_hash(item["title"])
            if h in seen: continue
            seen.add(h)
            item["source_name"] = feed["name"]
            all_items.append(item)
    
    for src in TELEGRAM_SOURCES:
        for item in fetch_telegram(src["url"]):
            h = news_hash(item["title"])
            if h in seen: continue
            seen.add(h)
            item["source_name"] = src["name"]
            all_items.append(item)
    
    with_img = [i for i in all_items if i.get("image_url")]
    without_img = [i for i in all_items if not i.get("image_url")]
    
    new_items = []
    for item in with_img:
        h = news_hash(item["title"])
        if h not in cache:
            cache[h] = time.time()
            new_items.append(item)
            if len(new_items) >= max_items: break
    
    if len(new_items) < max_items:
        for item in without_img:
            h = news_hash(item["title"])
            if h not in cache:
                cache[h] = time.time()
                new_items.append(item)
                if len(new_items) >= max_items: break
    
    save_cache(cache)
    return new_items

# ─── Translation (Auto-detect) ──────────────────────────────────

_translator_en = None
_translator_es = None

def _detect_lang(text):
    spanish_chars = set("áéíóúñ¿¡")
    if any(c in text.lower() for c in spanish_chars): return "es"
    return "en"

def _translate(text):
    global _translator_en, _translator_es
    if not text: return ""
    
    lang = _detect_lang(text)
    try:
        from deep_translator import GoogleTranslator
        if lang == "es":
            if _translator_es is None: _translator_es = GoogleTranslator(source="es", target="fa")
            return _translator_es.translate(text)
        else:
            if _translator_en is None: _translator_en = GoogleTranslator(source="en", target="fa")
            return _translator_en.translate(text)
    except Exception as e:
        print(f"[WARN] Translation failed: {e}")
        return text

# ─── Summary Builder ────────────────────────────────────────────

def build_summary(news_items):
    if not news_items: return ""
    
    now = datetime.now(timezone.utc)
    tehran = now + timedelta(hours=3, minutes=30)
    
    months_en = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    months_fa = ["ژانویه","فوریه","مارس","آوریل","مه","ژوئن","ژوئیه","اوت","سپتامبر","اکتبر","نوامبر","دسامبر"]
    weekdays = ["دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه","شنبه","یکشنبه"]
    
    date_str = tehran.strftime("%d %B %Y")
    for en, fa in zip(months_en, months_fa): date_str = date_str.replace(en, fa)
    weekday = weekdays[tehran.weekday()]
    
    lines = [
        "⚪ **خبرنامه رئال مادرید**",
        f"📅 {weekday} — {date_str}",
        "",
    ]
    
    seen = set()
    unique = []
    for item in news_items[:10]:
        key = re.sub(r"[^a-zA-Z0-9]", "", item["title"].lower())
        if key in seen: continue
        seen.add(key)
        title_fa = _translate(item["title"])
        unique.append({"title_fa": title_fa, "source": item.get("source_name", "")})
    
    if len(unique) >= 3:
        lines.append("🔹 " + " | ".join([i["title_fa"] for i in unique[:3]]))
        lines.append("")
        if len(unique) > 3:
            lines.append("🔸 " + " | ".join([i["title_fa"] for i in unique[3:6]]))
            lines.append("")
        if len(unique) > 6:
            lines.append("🔹 " + " | ".join([i["title_fa"] for i in unique[6:9]]))
            lines.append("")
    else:
        for item in unique:
            lines.append(f"⚪ {item['title_fa']}")
            lines.append("")
    
    sources = list(set(i["source"] for i in unique if i["source"]))
    if sources:
        lines.append(f"📎 **منابع:** {' — '.join(sources[:3])}")
    
    return "\n".join(lines)

# ─── Telegram Send ──────────────────────────────────────────────

def send_telegram(text, photo_url=None):
    """Send message to Telegram."""
    if photo_url:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        data = {"chat_id": ADMIN_CHAT_ID, "caption": text[:1024], "parse_mode": "Markdown", "photo": photo_url}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": "true"}
    
    import urllib.parse
    encoded = urllib.parse.urlencode(data).encode()
    req = Request(url, data=encoded, method="POST")
    
    try:
        with urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            if result.get("ok"):
                print(f"✅ Message sent successfully")
                return True
            else:
                print(f"❌ Telegram error: {result}")
                return False
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        return False

# ─── Main ───────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now().time()}] 🔍 Fetching Real Madrid news...")
    
    news = get_new_news(15)
    if not news:
        print("📭 No new news found. Skipping.")
        return
    
    print(f"📰 Found {len(news)} new items")
    
    summary = build_summary(news)
    if not summary:
        print("❌ Failed to build summary")
        return
    
    # Send with first image if available
    img_url = None
    for item in news:
        if item.get("image_url"):
            img_url = item["image_url"]
            break
    
    print(f"📤 Sending to Telegram...")
    send_telegram(summary, img_url)
    
    # Send additional items if more than 10
    if len(news) > 10:
        extra = build_summary(news[10:])
        if extra:
            send_telegram(extra)

if __name__ == "__main__":
    main()
