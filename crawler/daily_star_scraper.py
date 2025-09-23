"""
daily_star_scraper.py
=======================

This module provides a minimal scraper for The Daily Star (thedailystar.net)
news website.  Given a specific date, the script downloads the site's
``googlenews.xml`` feed, filters all entries published on that date and then
retrieves each article page to extract the headline and body text.

Rationale
---------
The Daily Star publishes a Google News‐compatible XML feed at
``https://www.thedailystar.net/googlenews.xml``.  Each entry in the feed is
wrapped in a ``<url>`` element and contains the article URL (``<loc>``),
title (``<news:title>``) and publication timestamp
(``<news:publication_date>``).  By filtering on the publication date you
can collect stories for “today” or any arbitrary day.  This scraper avoids
the heavier paginated sitemap index because the Google News feed already
exposes all recent articles in a compact format.

The scraper warms up a ``requests.Session`` on the homepage, applies
browser‑like HTTP headers to avoid simple bot blockers, and then fetches the
Google News feed.  Each article is retrieved with the same session and
parsed using BeautifulSoup.  The parser first inspects any JSON‑LD
``<script type="application/ld+json">`` blocks for an ``articleBody``
field.  If present, that text is used as the article body.  Otherwise, the
script falls back to a heuristic that searches for a ``div`` or ``section``
whose ``class`` or ``id`` attribute contains words like ``article`` or
``content``.  As a final fallback it concatenates all ``<p>`` tags from
the page.

Usage
-----
Run this script from the command line and pass an optional date argument
(``YYYY-MM-DD``).  If no date is supplied it defaults to today’s date.

Examples::

    python daily_star_scraper.py
    python daily_star_scraper.py 2025-09-19

The script prints a CSV to stdout with three columns: ``category``,
``title`` and ``url``.  The category is inferred from the first segment
of the article URL path.  If you need to persist the results, redirect
stdout to a file::

    python daily_star_scraper.py 2025-09-19 > daily_star_2025-09-19.csv

Note
----
This code is provided for educational and research purposes.  You are
responsible for complying with The Daily Star’s terms of service and
robots.txt.  According to the user’s investigation, the robots.txt allows
news aggregation and AI retrieval for current events, but prohibits other
types of automated scraping.  Use responsibly.
"""

from __future__ import annotations

import sys
import time
import re
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

# A reasonable browser‑like header set to reduce the chance of 403/429 responses.
HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
    "Referer": "https://www.google.com/",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}

# Regex patterns to extract information from the Google News XML feed
RE_URL_BLOCK = re.compile(r"<url>(.*?)</url>", re.S)
RE_LOC = re.compile(r"<loc>(.*?)</loc>", re.S)
RE_PUB_DATE = re.compile(r"<news:publication_date>(.*?)</news:publication_date>", re.S)
RE_TITLE = re.compile(r"<news:title>(.*?)</news:title>", re.S)


def fetch_googlenews_entries(
    session: requests.Session,
    date_prefix: str,
    timeout: int = 20,
    retries: int = 3,
    backoff: float = 1.5,
) -> List[Dict[str, str]]:
    """Fetch the Google News feed and extract entries published on a given date.

    Parameters
    ----------
    session : requests.Session
        A pre‑initialised session with cookies and headers.
    date_prefix : str
        Date string in ``YYYY-MM-DD`` format.  Only feed entries whose
        publication date begins with this prefix will be returned.

    Returns
    -------
    List[Dict[str, str]]
        A list of dictionaries with keys ``url``, ``title`` and ``pub_date``.
    """
    url = "https://www.thedailystar.net/googlenews.xml"
    xml = None
    last_exc: Optional[Exception] = None
    for attempt in range(max(1, retries)):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            xml = resp.text
            break
        except Exception as exc:
            last_exc = exc
            if attempt == retries - 1:
                # Give up and return empty on persistent failure
                return []
            # Exponential backoff before retrying
            time.sleep(backoff * (2 ** attempt))
    if not xml:
        return []

    entries: List[Dict[str, str]] = []
    for block in RE_URL_BLOCK.findall(xml):
        loc_match = RE_LOC.search(block)
        date_match = RE_PUB_DATE.search(block)
        title_match = RE_TITLE.search(block)
        if not (loc_match and date_match and title_match):
            continue
        loc = loc_match.group(1).strip()
        pub_date = date_match.group(1).strip()
        title_raw = title_match.group(1).strip()
        # Remove CDATA markers if present
        if title_raw.startswith("<![CDATA["):
            title_raw = title_raw[9:-3].strip()
        # Filter by date prefix
        if not pub_date.startswith(date_prefix):
            continue
        entries.append({
            "url": loc,
            "title": title_raw,
            "pub_date": pub_date,
        })
    return entries


def extract_article_text(soup: BeautifulSoup) -> str:
    """Extract the main article text from a BeautifulSoup document.

    The function first looks for ``<script type="application/ld+json">`` blocks
    containing an ``articleBody`` field.  If not found, it searches for
    elements whose ``id`` or ``class`` attributes match common article
    container patterns.  As a last resort it concatenates all ``<p>``
    elements in the document.

    Parameters
    ----------
    soup : BeautifulSoup
        Parsed HTML of an article page.

    Returns
    -------
    str
        A newline‑separated string containing the article’s paragraphs.
    """
    # JSON-LD extraction
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = tag.string or tag.get_text()
        if not text:
            continue
        try:
            data = json.loads(text)
        except Exception:
            # Some pages contain multiple JSON objects; attempt to recover the first
            match = re.search(r"\{.*?\}", text, flags=re.S)
            if not match:
                continue
            try:
                data = json.loads(match.group(0))
            except Exception:
                continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            article_body = item.get("articleBody")
            if article_body:
                # article_body may be a list or string
                if isinstance(article_body, list):
                    article_body = "\n".join(str(x) for x in article_body)
                # Remove HTML tags if present
                body_soup = BeautifulSoup(str(article_body), "html.parser")
                text = body_soup.get_text(separator="\n").strip()
                if text:
                    return text
    # Heuristic based on container class or id
    pattern = re.compile(
        r"(article|story|news|post).*(body|content|text|detail)|(^content$)|(^article$)",
        re.I,
    )
    candidates = []
    for tag in soup.find_all(True, attrs={"class": True}):
        classes = " ".join(tag.get("class", []))
        if pattern.search(classes):
            candidates.append(tag)
    for tag in soup.find_all(True, attrs={"id": True}):
        _id = tag.get("id", "")
        if pattern.search(_id):
            candidates.append(tag)
    # Choose the candidate with the most text
    best_text = ""
    for tag in candidates:
        text = tag.get_text(separator="\n").strip()
        if len(text) > len(best_text):
            best_text = text
    if len(best_text) > 200:
        return best_text
    # Fallback: concatenate all paragraph tags
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    return "\n".join(paragraphs).strip()


def fetch_article(session: requests.Session, url: str) -> Optional[Dict[str, str]]:
    """Retrieve and parse a single Daily Star article.

    Parameters
    ----------
    session : requests.Session
        The shared session used for all HTTP requests.
    url : str
        Absolute URL of the article to fetch.

    Returns
    -------
    Optional[Dict[str, str]]
        A dictionary with keys ``title``, ``body`` and ``category`` or
        ``None`` if the request fails or no meaningful content can be
        extracted.
    """
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else None
    body = extract_article_text(soup)
    if not title or not body:
        return None
    # Infer category from URL path (first segment)
    path_parts = [part for part in url.split("/") if part]
    category = "unknown"
    # The URL structure is .../news/<category>/<sub-category>/... or .../<category>/news/...
    # We attempt to pick the segment after the domain that is not ``news``.
    if len(path_parts) > 3:
        # path_parts[2] corresponds to the segment after the domain
        segment = path_parts[3]  # e.g. 'entertainment', 'sports'
        if segment != "news":
            category = segment
        elif len(path_parts) > 4:
            category = path_parts[4]
    return {
        "title": title,
        "body": body,
        "url": url,
        "category": category,
    }


def get_dailystar_headlines(max_articles: int = 5, max_days_fallback: int = 3) -> List[Dict[str, str]]:
    """
    Get Daily Star headlines (URL and title only) for today's date.
    
    Parameters
    ----------
    max_articles : int, optional
        Maximum number of articles to return. Default is 5.
    
    Returns
    -------
    List[Dict[str, str]]
        List of dictionaries with 'url', 'title', and 'category' keys.
    """
    # Get today's date and try fallback days if empty
    session = requests.Session()
    try:
        session.get("https://www.thedailystar.net/", headers=HEADERS, timeout=30)
    except Exception:
        pass

    today = datetime.today()
    for delta in range(0, max(0, max_days_fallback) + 1):
        date_str = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
        entries = fetch_googlenews_entries(session, date_str)
        if not entries:
            continue
        if len(entries) > max_articles:
            entries = entries[:max_articles]
        results = []
        for entry in entries:
            # Infer category from URL path (first segment)
            path_parts = [part for part in entry["url"].split("/") if part]
            category = "unknown"
            if len(path_parts) > 3:
                segment = path_parts[3]
                if segment != "news":
                    category = segment
                elif len(path_parts) > 4:
                    category = path_parts[4]
            results.append({
                "url": entry["url"],
                "title": entry["title"],
                "category": category,
            })
        if results:
            return results
    return []


def scrape_daily_star(date_str: str, max_articles: int = 10, delay: float = 1.5) -> List[Dict[str, str]]:
    """Scrape The Daily Star articles for a specific date.

    Parameters
    ----------
    date_str : str
        The date of interest in ``YYYY-MM-DD`` format.
    max_articles : int
        Maximum number of articles to scrape.
    delay : float
        Delay between requests in seconds.

    Returns
    -------
    List[Dict[str, str]]
        A list of dictionaries containing ``category``, ``title``, ``body`` and
        ``url`` keys for each article published on the given date.
    """
    session = requests.Session()
    # Warm up on the home page to collect cookies
    try:
        session.get("https://www.thedailystar.net/", headers=HEADERS, timeout=30)
    except Exception:
        pass
    
    # Extract feed entries
    entries = fetch_googlenews_entries(session, date_str)
    
    if len(entries) > max_articles:
        entries = entries[:max_articles]
    
    results: List[Dict[str, str]] = []
    import time
    
    for entry in entries:
        art = fetch_article(session, entry["url"])
        if not art:
            continue
        # Prefer the feed title over scraped <h1> if available
        art["title"] = entry["title"] or art["title"]
        # Add publication date from feed
        art["date_published"] = entry["pub_date"]
        results.append(art)
        time.sleep(delay)
    
    return results


def format_articles_as_string(articles: List[Dict[str, str]], date_str: str) -> str:
    """Format scraped articles as a readable string."""
    formatted_text = []
    
    # Add header
    header = f"""THE DAILY STAR NEWS SCRAPER
Date: {date_str}
Total Articles: {len(articles)}
Scraped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{' '*100}

"""
    formatted_text.append(header)
    
    for i, article in enumerate(articles, 1):
        # Add article separator
        formatted_text.append(f"{' '*100}")
        formatted_text.append(f"ARTICLE {i}")
        formatted_text.append(f"{' '*100}")
        
        # Add headline
        title = article.get("title") or "No Title Available"
        formatted_text.append(f"HEADLINE: {title}")
        formatted_text.append("")
        
        # Add URL
        url = article.get("url") or "No URL Available"
        formatted_text.append(f"URL: {url}")
        formatted_text.append("")
        
        # Add metadata
        category = article.get("category") or "Unknown"
        date_published = article.get("date_published") or "Unknown Date"
        
        formatted_text.append(f"Category: {category}")
        formatted_text.append(f"Date: {date_published}")
        formatted_text.append(" ")
        
        # Add news content
        body = article.get("body") or "No content available"
        formatted_text.append("NEWS CONTENT:")
        formatted_text.append("-" * 50)
        formatted_text.append(body)
        formatted_text.append("")
        formatted_text.append(" " * 50)
        formatted_text.append("")
        formatted_text.append("")
    
    return "\n".join(formatted_text)


def save_headlines_to_file(headlines: List[Dict[str, str]]) -> None:
    """
    Save only URL and title to a text file in the news folder.
    
    Parameters
    ----------
    headlines : List[Dict[str, str]]
        List of headline dictionaries with url, title, and category
    """
    # Get today's date automatically
    date_str = datetime.today().strftime("%Y-%m-%d")
    
    # Always save to the project-root news folder (independent of CWD)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_dir = os.path.join(project_root, "news")
    os.makedirs(news_dir, exist_ok=True)
    filename = os.path.join(news_dir, f"dailystar_headlines_{date_str}.txt")

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"THE DAILY STAR HEADLINES\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Total Headlines: {len(headlines)}\n")
            f.write(f"Scraped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 80}\n\n")
            
            for i, article in enumerate(headlines, 1):
                f.write(f"{i:3d}. {article['title']}\n")
                f.write(f"     URL: {article['url']}\n")
                f.write(f"     Category: {article['category']}\n\n")
        
    except Exception as e:
        pass


def main(argv: List[str] | None = None) -> None:
    headlines = get_dailystar_headlines(max_articles=20)
    
    # Always write a file, even if no headlines were found
    save_headlines_to_file(headlines)


if __name__ == "__main__":
    main(sys.argv)