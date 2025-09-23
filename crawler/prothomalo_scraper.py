from __future__ import annotations

import json
import time
import os
from typing import Iterable, List, Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ---------- HTTP helpers ----------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
}

def fetch_sitemap_urls(sitemap_url: str) -> List[str]:
    """Fetch and parse a sitemap XML to extract all URLs (lightweight parser)."""
    try:
        resp = requests.get(sitemap_url, headers=DEFAULT_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        return []

    urls: List[str] = []
    text = resp.text
    # Simple and fast: split by <loc> to pull URLs without full XML parsing.
    for part in text.split("<loc>")[1:]:
        loc, *_ = part.split("</loc>", 1)
        loc = loc.strip()
        if loc:
            urls.append(loc)
    return urls

def filter_urls_by_sections(urls: Iterable[str], sections: Iterable[str]) -> List[str]:
    """Keep URLs whose path contains any of the given section slugs."""
    wanted = set(sections)
    matched: List[str] = []
    for url in urls:
        path_parts = urlparse(url).path.strip("/").split("/")
        if any(part in wanted for part in path_parts):
            matched.append(url)
    return matched

# ---------- Minimal title extraction ----------

def extract_title_from_html(html: str) -> Optional[str]:
    """Try multiple strategies to find a reasonable article title."""
    soup = BeautifulSoup(html, "html.parser")

    # 1 JSON-LD: Search for Article/NewsArticle headline
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not tag.string:
            continue
        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError:
            continue

        # Normalize to iterable of dicts
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            # Some sites nest graph items
            graph = item.get("@graph")
            if isinstance(graph, list):
                candidates.extend([n for n in graph if isinstance(n, dict)])
            # Look for headline
            headline = item.get("headline")
            if isinstance(headline, str) and headline.strip():
                return headline.strip()

    # 2) Open Graph meta
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()

    # 3) <title>
    if soup.title and soup.title.string:
        t = soup.title.string.strip()
        if t:
            return t

    # 4) <h1>
    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(strip=True)
        if t:
            return t

    return None

def fetch_title(url: str, delay: float = 0.5) -> Optional[str]:
    """Fetch a page and return just the best-effort title."""
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    finally:
        # be polite between requests
        time.sleep(delay)

    return extract_title_from_html(resp.text)

# ---------- Public API ----------

def get_prothomalo_headlines(
    sections: List[str] | None = None,
    max_articles_per_section: int = 2,
    delay_between_requests: float = 0.5,
    max_days_fallback: int = 3,
) -> List[Dict[str, str]]:
    """
    Return URL+title headlines from Prothom Alo's daily sitemap for today's date.

    Parameters
    ----------
    sections : List[str], optional
        Section slugs to filter by. Defaults to common sections.
    max_articles_per_section : int
        Cap per section after filtering.
    delay_between_requests : float
        Sleep between per-URL fetches to reduce load.

    Returns
    -------
    List[Dict[str, str]] with keys: url, title, section
    """
    # Helper to build results from a list of urls
    def _build_results(urls: List[str], use_sections: Optional[List[str]]) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        if use_sections:
            for sec in use_sections:
                for u in filter_urls_by_sections(urls, [sec])[:max_articles_per_section]:
                    title = fetch_title(u, delay=delay_between_requests)
                    if title:
                        items.append({"url": u, "title": title, "section": sec})
        else:
            # No section filtering: take a reasonable cap (per-section * number of typical sections)
            cap = max(1, max_articles_per_section * 7)
            for u in urls[:cap]:
                title = fetch_title(u, delay=delay_between_requests)
                if title:
                    # Attempt to infer a section from path; fallback to 'unknown'
                    path_parts = urlparse(u).path.strip("/").split("/")
                    inferred = path_parts[0] if path_parts and path_parts[0] else "unknown"
                    items.append({"url": u, "title": title, "section": inferred})
        return items

    # Default sections list (English slugs may not match Bengali URLs; we will fallback if empty)
    default_sections = [
        "bangladesh", "sports", "politics", "business", "entertainment", "lifestyle", "world"
    ]
    use_sections = default_sections if sections is None else sections

    # Try today then fallback to previous days up to max_days_fallback
    today = datetime.today()
    for delta in range(0, max(0, max_days_fallback) + 1):
        date_str = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
        sitemap_url = f"https://www.prothomalo.com/sitemap/sitemap-daily-{date_str}.xml"
        urls = fetch_sitemap_urls(sitemap_url)
        if not urls:
            continue
        # First, try with sections (if provided / default)
        results = _build_results(urls, use_sections)
        if results:
            return results
        # Fallback: no section filtering (handles Bengali slugs)
        results = _build_results(urls, None)
        if results:
            return results
    return []

def save_headlines_to_file(headlines: List[Dict[str, str]]) -> None:
    """Persist URL+title+section to a simple UTF-8 text file in news folder."""
    # Get today's date automatically
    date_str = datetime.today().strftime("%Y-%m-%d")
    
    # Always save to the project-root news folder (independent of CWD)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_dir = os.path.join(project_root, "news")
    os.makedirs(news_dir, exist_ok=True)
    filename = os.path.join(news_dir, f"prothomalo_headlines_{date_str}.txt")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("PROTHOM ALO HEADLINES\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Total Headlines: {len(headlines)}\n")
            f.write(f"Scraped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            for i, item in enumerate(headlines, 1):
                f.write(f"{i:3d}. {item['title']}\n")
                f.write(f"     URL: {item['url']}\n")
                f.write(f"     Section: {item['section']}\n\n")
    except Exception as e:
        pass

def get_todays_date() -> str:
    return datetime.today().strftime("%Y-%m-%d")

# ---------- CLI entry ----------
def main():
    headlines = get_prothomalo_headlines(max_articles_per_section=2)
    # Always write an output file (it will contain 0 count if empty)
    save_headlines_to_file(headlines)
if __name__ == "__main__":
    main()
