"""
Real Madrid Players Module
Fetches players from multiple sources with fallback.
"""
import os
import json
import re
import requests
from typing import List, Dict, Optional
from datetime import datetime

# ─── Hardcoded 2024-25 Squad (Fall back) ──────────────────────────
HARDCODED_PLAYERS = [
    {"number": 1, "name": "Courtois", "position": "GK"},
    {"number": 2, "name": "Carvajal", "position": "RB"},
    {"number": 3, "name": "Militão", "position": "CB"},
    {"number": 4, "name": "Alaba", "position": "CB"},
    {"number": 5, "name": "Valverde", "position": "CM"},
    {"number": 6, "name": "Camavinga", "position": "CM"},
    {"number": 7, "name": "Vinícius Jr.", "position": "LW"},
    {"number": 8, "name": "Kroos", "position": "CM"},  # Retired but legacy
    {"number": 9, "name": "Mbappé", "position": "ST"},
    {"number": 10, "name": "Modrić", "position": "CM"},
    {"number": 11, "name": "Rodrygo", "position": "RW"},
    {"number": 12, "name": "Güler", "position": "AM"},
    {"number": 13, "name": "Lunin", "position": "GK"},
    {"number": 14, "name": "Tchouaméni", "position": "CDM"},
    {"number": 15, "name": "Güendouzi", "position": "CM"},
    {"number": 16, "name": "Endrick", "position": "ST"},
    {"number": 17, "name": "Lucas V.", "position": "RB"},
    {"number": 18, "name": "Rüdiger", "position": "CB"},
    {"number": 19, "name": "Ceballos", "position": "CM"},
    {"number": 20, "name": "Brahim", "position": "AM"},
    {"number": 21, "name": "Díaz", "position": "AM"},
    {"number": 22, "name": "Fran García", "position": "LB"},
    {"number": 23, "name": "Ferland Mendy", "position": "LB"},
    {"number": 24, "name": "Vinícius Tobias", "position": "RB"},
    {"number": 25, "name": "Arribas", "position": "CM"},
    {"number": 26, "name": "Paz", "position": "AM"},
    {"number": 27, "name": "Jacobo", "position": "CB"},
    {"number": 28, "name": "Gonzalo", "position": "GK"},
    {"number": 29, "name": "Mario Martín", "position": "CDM"},
    {"number": 30, "name": "Víctor", "position": "CB"},
    {"number": 31, "name": "Sergio", "position": "CM"},
]

THESPORTSDB_API = "https://www.thesportsdb.com/api/v1/json/3"
REAL_MADRID_ID = "133674"  # TheSportsDB team ID for Real Madrid


def _clean_player_name(name: str) -> str:
    """Clean player name for consistent matching."""
    # Remove accents, normalize
    name = name.replace("í", "i").replace("ó", "o").replace("á", "a").replace("é", "e").replace("ú", "u")
    name = name.replace("ñ", "n").replace("ü", "u")
    return name.strip()


def _normalize_for_search(name: str) -> str:
    """Normalize name for fuzzy matching in news."""
    return re.sub(r"[^a-zA-Z0-9]", "", name.lower())


def fetch_from_thesportsdb() -> List[Dict]:
    """Fetch Real Madrid players from TheSportsDB API."""
    try:
        url = f"{THESPORTSDB_API}/lookup_all_players.php?id={REAL_MADRID_ID}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        players = data.get("player", []) if data else []
        
        result = []
        for p in players:
            num = p.get("strNumber")
            name = p.get("strPlayer")
            pos = p.get("strPosition")
            # Filter: only current squad (strStatus = "Active" or no status)
            status = p.get("strStatus", "")
            # Also check if player is actually Real Madrid (some APIs mix)
            team = p.get("strTeam", "")
            if team and "Real Madrid" not in team:
                continue
            if num and name and num.isdigit():
                result.append({
                    "number": int(num),
                    "name": name.strip(),
                    "position": pos or "",
                })
        
        # Sort by number
        result.sort(key=lambda x: x["number"])
        return result
    except Exception as e:
        print(f"TheSportsDB fetch failed: {e}")
        return []


def fetch_from_official_site() -> List[Dict]:
    """Scrape Real Madrid official site for current squad."""
    try:
        # Official squad page
        url = "https://www.realmadrid.com/en/football/squad"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; RealMadridBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        # Parse HTML for player cards
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        
        result = []
        # Look for player cards - structure varies
        for card in soup.select(".player-card, .squad-player, [class*='player']"):
            num_elem = card.select_one("[class*='number'], .shirt-number, .number")
            name_elem = card.select_one("[class*='name'], .player-name, h3, h4")
            pos_elem = card.select_one("[class*='position'], .pos")
            
            num = num_elem.get_text(strip=True) if num_elem else ""
            name = name_elem.get_text(strip=True) if name_elem else ""
            pos = pos_elem.get_text(strip=True) if pos_elem else ""
            
            if num and name and num.isdigit():
                result.append({
                    "number": int(num),
                    "name": name,
                    "position": pos,
                })
        
        result.sort(key=lambda x: x["number"])
        return result
    except Exception as e:
        print(f"Official site scrape failed: {e}")
        return []


def _deduplicate_players(players: List[Dict]) -> List[Dict]:
    """Remove duplicates by number, keep first."""
    seen = set()
    unique = []
    for p in players:
        num = p.get("number")
        if num and num not in seen:
            seen.add(num)
            unique.append(p)
    return unique


def get_players(use_cache: bool = True, cache_hours: int = 24) -> List[Dict]:
    """
    Get Real Madrid current squad.
    Tries: TheSportsDB → Official Site → Hardcoded fallback.
    Caches result for cache_hours.
    """
    cache_file = os.path.join(os.path.dirname(__file__), "players_cache.json")

    # Check cache
    if use_cache and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            cached_time = datetime.fromisoformat(cache["timestamp"])
            if (datetime.now() - cached_time).total_seconds() < cache_hours * 3600:
                print(f"Using cached players ({len(cache['players'])} players)")
                return cache["players"]
        except Exception:
            pass

    # Try sources in order
    all_players = []

    # 1. TheSportsDB (most reliable structured data)
    print("Fetching from TheSportsDB...")
    thesportsdb_players = fetch_from_thesportsdb()
    if thesportsdb_players:
        print(f"TheSportsDB: {len(thesportsdb_players)} players")
        # Validate: must have key players like Courtois, Modric, Vinicius
        names = [p["name"].lower() for p in thesportsdb_players]
        key_players = ["courtois", "modric", "vinicius", "valverde", "rodrygo", "mbappe"]
        found = sum(1 for kp in key_players if any(kp in n for n in names))
        if found >= 3:  # At least 3 key players found
            all_players.extend(thesportsdb_players)
        else:
            print(f"TheSportsDB data incomplete (only {found}/6 key players), using fallback")
    else:
        print("TheSportsDB: no data returned")

    # 2. Official site (for validation/updates)
    if not all_players:
        print("Fetching from official site...")
        official_players = fetch_from_official_site()
        if official_players:
            print(f"Official site: {len(official_players)} players")
            names = [p["name"].lower() for p in official_players]
            key_players = ["courtois", "modric", "vinicius", "valverde", "rodrygo", "mbappe"]
            found = sum(1 for kp in key_players if any(kp in n for n in names))
            if found >= 3:
                all_players.extend(official_players)
            else:
                print(f"Official site data incomplete (only {found}/6 key players)")
        else:
            print("Official site: no data returned")

    # 3. Hardcoded fallback (always works)
    if not all_players:
        print("Using hardcoded fallback...")
        all_players = HARDCODED_PLAYERS.copy()

    # Deduplicate and sort
    all_players = _deduplicate_players(all_players)
    all_players.sort(key=lambda x: x.get("number", 999))

    # Cache result
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "players": all_players
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Cache write failed: {e}")

    print(f"Final squad: {len(all_players)} players")
    return all_players


def format_players_list(players: List[Dict]) -> str:
    """Format players list for Telegram display."""
    lines = ["⚽ **لیست بازیکنان رئال مادرید**\n"]
    for p in players:
        num = p.get("number", "")
        name = p.get("name", "")
        lines.append(f"{num}. {name}")
    lines.append(f"\n📊 کل: {len(players)} بازیکن")
    return "\n".join(lines)


def find_player_by_number(players: List[Dict], number: int) -> Optional[Dict]:
    """Find player by shirt number."""
    for p in players:
        if p.get("number") == number:
            return p
    return None


def find_player_by_name(players: List[Dict], name: str) -> Optional[Dict]:
    """Find player by name (fuzzy match)."""
    name_norm = _normalize_for_search(name)
    for p in players:
        if _normalize_for_search(p.get("name", "")) == name_norm:
            return p
        # Partial match
        if name_norm in _normalize_for_search(p.get("name", "")):
            return p
    return None


# ─── Search keywords for player news ─────────────────────────────
def get_player_search_terms(player: Dict) -> List[str]:
    """Get search terms to find news for a specific player."""
    name = player.get("name", "")
    terms = [name]
    
    # Add common variations
    if " " in name:
        parts = name.split()
        # First + last name
        terms.append(f"{parts[0]} {parts[-1]}")
        # Just last name
        terms.append(parts[-1])
    
    # Special cases
    if "Vinícius" in name or "Vinicius" in name:
        terms.extend(["Vinicius Jr", "Vini Jr", "Vini"])
    elif "Mbappé" in name or "Mbappe" in name:
        terms.extend(["Kylian Mbappe", "Kylian"])
    elif "Rodrygo" in name:
        terms.extend(["Rodrygo Goes"])
    elif "Valverde" in name:
        terms.extend(["Fede Valverde", "Federico Valverde"])
    elif "Camavinga" in name:
        terms.extend(["Eduardo Camavinga"])
    elif "Tchouaméni" in name or "Tchouameni" in name:
        terms.extend(["Aurelien Tchouameni"])
    elif "Militão" in name or "Militao" in name:
        terms.extend(["Eder Militao"])
    elif "Rüdiger" in name or "Rudiger" in name:
        terms.extend(["Antonio Rudiger"])
    elif "Alaba" in name:
        terms.extend(["David Alaba"])
    elif "Carvajal" in name:
        terms.extend(["Dani Carvajal"])
    elif "Modrić" in name or "Modric" in name:
        terms.extend(["Luka Modric"])
    elif "Courtois" in name:
        terms.extend(["Thibaut Courtois"])
    elif "Lunin" in name:
        terms.extend(["Andriy Lunin"])
    elif "Endrick" in name:
        terms.extend(["Endrick Felipe"])
    elif "Güler" in name or "Guler" in name:
        terms.extend(["Arda Guler"])
    elif "Brahim" in name:
        terms.extend(["Brahim Diaz"])
    elif "Ceballos" in name:
        terms.extend(["Dani Ceballos"])
    elif "Ferland Mendy" in name or "Mendy" in name:
        terms.extend(["Ferland Mendy"])
    elif "Fran García" in name or "Fran Garcia" in name:
        terms.extend(["Fran Garcia"])
    elif "Lucas V" in name or "Lucas V." in name:
        terms.extend(["Lucas Vazquez", "Lucas Vázquez"])
    
    # Deduplicate
    seen = set()
    unique = []
    for t in terms:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique.append(t)
    
    return unique


if __name__ == "__main__":
    # Test
    players = get_players(use_cache=False)
    print(format_players_list(players))
    print("\n--- Search terms for Vinícius Jr. ---")
    vini = find_player_by_name(players, "Vinícius Jr.")
    if vini:
        print(get_player_search_terms(vini))