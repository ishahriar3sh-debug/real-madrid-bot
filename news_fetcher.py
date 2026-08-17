"""
Real Madrid News Bot — RSS News Fetcher
Fetches and parses Real Madrid news from multiple sources:
- RSS feeds (Google News, BBC Sport, Marca) with images
- Telegram channels (@Realmadridfarsi)
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

# XML namespaces for media:content
NS_MEDIA = {"media": "http://search.yahoo.com/mrss/"}


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
    """Parse RSS XML into a list of news items with images."""
    items = []
    if not xml_text:
        return items

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

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

        # Extract image from media:content or enclosure
        image_url = ""
        media_contents = item.findall("media:content", NS_MEDIA)
        if media_contents:
            image_url = media_contents[0].get("url", "")
        else:
            enclosure = item.find("enclosure")
            if enclosure is not None and "image" in enclosure.get("type", ""):
                image_url = enclosure.get("url", "")

        if title:
            items.append({
                "title": title,
                "link": link,
                "description": description[:200],
                "pub_date": pub_date,
                "source": source,
                "image_url": image_url,
            })

    return items


def fetch_telegram_channel(channel_url: str, timeout: int = 15) -> list[dict]:
    """Fetch posts from a public Telegram channel via web preview."""
    req = Request(channel_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, TimeoutError, OSError) as e:
        print(f"[WARN] Failed to fetch Telegram channel {channel_url}: {e}")
        return []

    items = []
    # Extract message blocks with text and optional images
    message_blocks = re.findall(
        r'class="tgme_widget_message_wrap[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )

    for block in message_blocks[:20]:
        # Extract text
        text_match = re.search(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            block,
            re.DOTALL,
        )
        if not text_match:
            continue
        text = clean_html(text_match.group(1))
        if len(text) < 20:
            continue

        # Extract image if present
        image_url = ""
        img_match = re.search(
            r'class="tgme_widget_message_photo_wrap"[^>]*style="background-image:url\(&#039;([^&]+)',
            block,
        )
        if img_match:
            image_url = img_match.group(1)

        title = text[:150].strip()
        if title:
            items.append({
                "title": title,
                "link": channel_url,
                "description": text[:200],
                "pub_date": "",
                "source": "Telegram",
                "image_url": image_url,
            })

    return items


def fetch_all_news(feeds: list[dict], telegram_sources: list[dict] = None, filter_keyword: str = "real madrid") -> list[dict]:
    """Fetch news from all configured RSS feeds and Telegram channels."""
    all_items = []
    seen_titles = set()
    keyword = filter_keyword.lower()

    # Fetch from RSS feeds
    for feed in feeds:
        xml_text = fetch_feed(feed["url"])
        if not xml_text:
            continue

        items = parse_feed(xml_text)
        feed_filter = feed.get("filter", keyword)

        for item in items:
            # Skip filter if empty (for curated feeds like Marca Real Madrid)
            if feed_filter:
                title_lower = item["title"].lower()
                if feed_filter not in title_lower and feed_filter not in item.get("description", "").lower():
                    continue

            # Dedup
            title_key = news_hash(item["title"])
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            item["source_name"] = feed["name"]
            all_items.append(item)

    # Fetch from Telegram channels
    if telegram_sources:
        for source in telegram_sources:
            items = fetch_telegram_channel(source["url"])
            for item in items:
                title_key = news_hash(item["title"])
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                item["source_name"] = source["name"]
                all_items.append(item)

    return all_items


def get_new_news(feeds: list[dict], telegram_sources: list[dict] = None, max_items: int = 15) -> list[dict]:
    """Get news that hasn't been sent before. Prioritizes items with images."""
    cache = load_cache()
    all_news = fetch_all_news(feeds, telegram_sources)

    # Separate items with and without images
    with_images = [item for item in all_news if item.get("image_url")]
    without_images = [item for item in all_news if not item.get("image_url")]

    new_items = []

    # First, add items with images (prioritize visual content)
    for item in with_images:
        h = news_hash(item["title"])
        if h not in cache:
            cache[h] = time.time()
            new_items.append(item)
            if len(new_items) >= max_items:
                break

    # Then fill remaining slots with items without images
    if len(new_items) < max_items:
        for item in without_images:
            h = news_hash(item["title"])
            if h not in cache:
                cache[h] = time.time()
                new_items.append(item)
                if len(new_items) >= max_items:
                    break

    save_cache(cache)
    return new_items


def get_player_news(feeds: list[dict], telegram_sources: list[dict], player_name: str, 
                    max_items: int = 10, hours_back: int = 168) -> list[dict]:
    """
    Get news specifically about a player from the last N hours (default 1 week).
    """
    import time
    from datetime import datetime, timezone
    
    all_news = fetch_all_news(feeds, telegram_sources)
    
    # Get search terms for this player
    from players import get_player_search_terms
    search_terms = get_player_search_terms({"name": player_name})
    
    # Time cutoff
    cutoff_time = time.time() - (hours_back * 3600)
    
    player_news = []
    seen_hashes = set()
    
    for item in all_news:
        title_lower = item["title"].lower()
        desc_lower = item.get("description", "").lower()
        
        # Check if any search term matches
        matched = False
        for term in search_terms:
            term_lower = term.lower()
            if term_lower in title_lower or term_lower in desc_lower:
                matched = True
                break
        
        if not matched:
            continue
        
        # Dedup
        h = news_hash(item["title"])
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        
        # Check if recent enough (if pub_date available)
        # We'll include all and let caller filter by time if needed
        
        player_news.append(item)
        if len(player_news) >= max_items:
            break
    
    # Sort by relevance (items with player name in title first)
    def relevance_score(item):
        title_lower = item["title"].lower()
        score = 0
        for term in search_terms:
            if term.lower() in title_lower:
                score += 10
            elif term.lower() in item.get("description", "").lower():
                score += 5
        return score
    
    player_news.sort(key=relevance_score, reverse=True)
    return player_news


if __name__ == "__main__":
    """Test the news fetcher."""
    from config import RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE

    print("🔍 در حال دریافت اخبار...\n")
    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
    
    if news:
        print(f"✅ {len(news)} خبر جدید پیدا شد:\n")
        with_img = sum(1 for n in news if n.get("image_url"))
        print(f"   📷 {with_img} خبر با تصویر")
        print(f"   📝 {len(news) - with_img} خبر بدون تصویر\n")
        for i, item in enumerate(news[:10], 1):
            source = item.get("source_name", "")
            has_img = "📷" if item.get("image_url") else "  "
            print(f"{i}. {has_img} [{source}] {item['title'][:80]}")
    else:
        print("📭 خبر جدیدی یافت نشد.")
