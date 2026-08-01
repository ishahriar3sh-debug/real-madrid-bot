"""
Real Madrid News Bot — RSS News Fetcher
Fetches and parses Real Madrid news from multiple RSS sources.
"""
import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from urllib.request import Request, urlopen
from urllib.error import URLError

CACHE_FILE = os.path.join(os.path.dirname(__file__), "seen_news.json")
USER_AGENT = "RealMadridNewsBot/1.0 (Python; +https://github.com)"


def load_cache() -> dict:
    """Load previously seen news hashes."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_cache(cache: dict):
    """Save seen news hashes (keep only last 48h)."""
    cutoff = time.time() - 48 * 3600
    cleaned = {k: v for k, v in cache.items() if v > cutoff}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f)


def clean_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def news_hash(title: str) -> str:
    """Create a hash for deduplication."""
    normalized = re.sub(r"[^a-zA-Z0-9]", "", title.lower())
    return hashlib.md5(normalized.encode()).hexdigest()


def fetch_feed(feed_url: str, timeout: int = 15) -> str:
    """Fetch RSS feed content."""
    req = Request(feed_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, TimeoutError, OSError) as e:
        print(f"[WARN] Failed to fetch {feed_url}: {e}")
        return ""


def parse_feed(xml_text: str) -> list[dict]:
    """Parse RSS XML into a list of news items."""
    items = []
    if not xml_text:
        return items

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    # Handle both RSS 2.0 and Atom
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    # RSS 2.0
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        pub_el = item.find("pubDate")
        source_el = item.find("source")

        title = clean_html(title_el.text if title_el is not None else "")
        link = link_el.text if link_el is not None else ""
        description = clean_html(desc_el.text if desc_el is not None else "")
        pub_date = pub_el.text if pub_el is not None else ""
        source = source_el.text if source_el is not None else source_el.get("url", "") if source_el is not None else ""

        if title:
            items.append({
                "title": title,
                "link": link,
                "description": description[:200],
                "pub_date": pub_date,
                "source": source,
            })

    return items


def fetch_all_news(feeds: list[dict], filter_keyword: str = "real madrid") -> list[dict]:
    """Fetch news from all configured RSS feeds."""
    all_items = []
    seen_titles = set()
    keyword = filter_keyword.lower()

    for feed in feeds:
        xml_text = fetch_feed(feed["url"])
        if not xml_text:
            continue

        items = parse_feed(xml_text)
        feed_filter = feed.get("filter", keyword)

        for item in items:
            title_lower = item["title"].lower()
            # Filter: title or description must contain the keyword
            if feed_filter not in title_lower and feed_filter not in item.get("description", "").lower():
                continue
            # Dedup within this fetch
            title_key = news_hash(item["title"])
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            item["source_name"] = feed["name"]
            all_items.append(item)

    return all_items


def get_new_news(feeds: list[dict], max_items: int = 5) -> list[dict]:
    """Get news that hasn't been sent before."""
    cache = load_cache()
    all_news = fetch_all_news(feeds)

    new_items = []
    for item in all_news:
        h = news_hash(item["title"])
        if h not in cache:
            cache[h] = time.time()
            new_items.append(item)
            if len(new_items) >= max_items:
                break

    save_cache(cache)
    return new_items


def format_news_message(items: list[dict], header: str = "") -> str:
    """Format news items into a beautiful Telegram message."""
    if not items:
        return ""

    lines = []
    if header:
        lines.append(header)
        lines.append("")

    for i, item in enumerate(items, 1):
        source = item.get("source_name", "")
        source_badge = f" [{source}]" if source else ""
        
        lines.append(f"**{i}.** {item['title']}")
        if item.get("description"):
            lines.append(f"   _{item['description'][:120]}..._")
        if item.get("link"):
            lines.append(f"   🔗 [ادامه خبر]({item['link']})")
        lines.append(f"   {source_badge}")
        lines.append("")

    lines.append(f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines)


if __name__ == "__main__":
    """Test the news fetcher."""
    from config import RSS_FEEDS, MAX_NEWS_PER_UPDATE

    print("🔍 Fetching Real Madrid news...\n")
    news = get_new_news(RSS_FEEDS, MAX_NEWS_PER_UPDATE)
    
    if news:
        msg = format_news_message(news, "⚽ **آخرین اخبار رئال مادرید**")
        print(msg)
        print(f"\n✅ {len(news)} خبر جدید پیدا شد.")
    else:
        print("📭 خبر جدیدی یافت نشد.")
