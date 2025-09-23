"""
jugantor_scraper.py
====================

This script scrapes headlines from the **Jugantor** news site for a given date
by parsing its Google News sitemap.  Jugantor exposes a ``news_sitemap.xml``
where each article entry includes the URL, publication timestamp, title and
keywords.  The scraper uses this structured data to collect article URLs and
headlines without fetching every article page.

Usage
-----

Run the script with an optional date (``YYYY-MM-DD``) to retrieve articles
published on that day.  If no date is provided, it defaults to the current
system date.

::

    python jugantor_scraper.py 2025-09-19

The output is printed to standard output as CSV with the columns
``category,title,url``.  The ``category`` is inferred from the first
path segment of the article URL (e.g. ``country-news`` or ``national``).

Network Considerations
----------------------

If the initial request to the sitemap encounters a ``403 Forbidden`` error,
try adding a short delay and reusing a ``requests.Session`` with a warm‑up
request to the homepage, similar to the Samakal scraper.  Jugantor’s
``news_sitemap.xml`` is accessible at the time of writing without special
headers, but robust error handling is included in case of network changes.
"""

from __future__ import annotations

import sys
import re
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# Define a simple User‑Agent to identify the scraper.  Jugantor’s sitemap
# currently allows access without a User‑Agent header, but setting one is
# polite.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
}


def fetch_news_sitemap() -> Optional[str]:
    """Download the Jugantor news sitemap XML.

    Returns the raw XML as a string, or ``None`` if the request fails.
    """
    url = "https://www.jugantor.com/news_sitemap.xml"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        return None


def parse_news_sitemap(xml_text: str, date_str: str) -> List[Dict[str, str]]:
    """Parse the news sitemap and return articles published on a specific date.

    Parameters
    ----------
    xml_text: str
        The raw XML content of the ``news_sitemap.xml`` file.
    date_str: str
        Desired publication date in ``YYYY-MM-DD`` format.

    Returns
    -------
    List[Dict[str, str]]
        Each dict contains ``url``, ``title``, ``category``.
    """
    soup = BeautifulSoup(xml_text, "xml")
    items: List[Dict[str, str]] = []
    for url_tag in soup.find_all("url"):
        loc = url_tag.find("loc")
        news_tag = url_tag.find("news:news")
        if not (loc and news_tag):
            continue
        pub_date_tag = news_tag.find("news:publication_date")
        title_tag = news_tag.find("news:title")
        if not (pub_date_tag and title_tag):
            continue
        pub_date = pub_date_tag.get_text()
        # Keep only entries whose date matches date_str
        # Publication_date is in ISO format, e.g. '2025-09-19T18:40:59+06:00'
        if not pub_date.startswith(date_str):
            continue
        url = loc.get_text().strip()
        title = title_tag.get_text().strip()
        category = infer_category_from_url(url)
        items.append({"url": url, "title": title, "category": category})
    return items


def get_jugantor_headlines(max_articles: int = 20) -> List[Dict[str, str]]:
    """
    Get Jugantor headlines (URL and title only) for today's date from sitemap.
    
    Parameters
    ----------
    max_articles : int, optional
        Maximum number of articles to return. Default is 20.
    
    Returns
    -------
    List[Dict[str, str]]
        List of dictionaries with 'url', 'title', and 'category' keys.
    """
    # Get today's date automatically
    date_str = datetime.today().strftime("%Y-%m-%d")
    
    xml = fetch_news_sitemap()
    if not xml:
        return []
    
    # Parse sitemap to get basic info (no need to fetch full articles)
    articles = parse_news_sitemap(xml, date_str)
    
    if len(articles) > max_articles:
        articles = articles[:max_articles]
    
    return articles


def save_headlines_to_file(headlines: List[Dict[str, str]]) -> None:
    """
    Save only URL and title to a text file in news folder.
    """
    # Get today's date automatically
    date_str = datetime.today().strftime("%Y-%m-%d")
    
    # Always save to the project-root news folder (independent of CWD)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_dir = os.path.join(project_root, "news")
    os.makedirs(news_dir, exist_ok=True)
    filename = os.path.join(news_dir, f"jugantor_headlines_{date_str}.txt")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"JUGANTOR HEADLINES\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Total Headlines: {len(headlines)}\n")
            f.write(f"Scraped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{' ' * 80}\n\n")
            
            for i, article in enumerate(headlines, 1):
                f.write(f"{i:3d}. {article['title']}\n")
                f.write(f"     URL: {article['url']}\n")
                f.write(f"     Category: {article['category']}\n\n")
    except Exception as e:
        pass


def infer_category_from_url(url: str) -> str:
    """Infer the news category from the first path segment of the URL."""
    path_parts = urlparse(url).path.strip("/").split("/")
    if path_parts:
        return path_parts[0]  # e.g. 'country-news', 'national', 'sports'
    return "unknown"


def parse_article(url: str) -> Optional[Dict[str, Optional[str]]]:
    """Parse a single article from Jugantor and extract its content.
    
    Parameters
    ----------
    url: str
        The URL of the article to parse.
    
    Returns
    -------
    Optional[Dict[str, Optional[str]]]
        Dictionary containing article data or None if parsing failed.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Initialize article dict
    article: Dict[str, Optional[str]] = {
        "url": url,
        "title": None,
        "date_published": None,
        "authors": None,
        "category": infer_category_from_url(url),
        "body": None,
    }
    
    # Try to extract from JSON-LD first
    json_data = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not tag.string:
            continue
        try:
            data = json.loads(tag.string)
            json_data.append(data)
        except json.JSONDecodeError:
            continue
    
    # Process JSON-LD data
    for data in json_data:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("headline"):
                    data = item
                    break
            else:
                continue
        
        if isinstance(data, dict) and data.get("headline"):
            article["title"] = data.get("headline")
            article["date_published"] = data.get("datePublished") or data.get("dateCreated")
            
            # Extract authors
            authors = data.get("author")
            if isinstance(authors, list):
                names = []
                for a in authors:
                    if isinstance(a, dict):
                        name = a.get("name") or a.get("givenName")
                        if name:
                            names.append(name)
                article["authors"] = ", ".join(names)
            elif isinstance(authors, dict):
                article["authors"] = authors.get("name") or authors.get("givenName")
            
            # Extract article body
            body_html = data.get("articleBody")
            if body_html:
                if isinstance(body_html, list):
                    body_html = "\n".join(str(item) for item in body_html)
                body_soup = BeautifulSoup(body_html, "html.parser")
                article["body"] = body_soup.get_text(separator="\n").strip()
            break
    
    # Fallback: extract from HTML elements if JSON-LD didn't work
    if not article["title"]:
        # Try common title selectors for Jugantor
        title_selectors = [
            "h1.news-title",
            "h1.headline",
            "h1.title",
            ".article-title h1",
            ".post-title h1",
            "h1",
            ".entry-title"
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                article["title"] = title_elem.get_text(strip=True)
                break
    
    if not article["body"]:
        # Try common content selectors for Jugantor
        content_selectors = [
            ".news-content",
            ".article-content", 
            ".post-content",
            ".entry-content",
            ".article-body",
            ".content-body",
            ".news-details"
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove script and style elements
                for script in content_elem(["script", "style", "nav", "aside"]):
                    script.decompose()
                article["body"] = content_elem.get_text(separator="\n", strip=True)
                break
        
        # If still no content, try to get all paragraphs
        if not article["body"]:
            paragraphs = soup.find_all("p")
            if paragraphs:
                article["body"] = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    
    return article


def scrape_jugantor(date_str: str, max_articles: int = 30, delay: float = 1.5) -> List[Dict[str, Optional[str]]]:
    """Scrape Jugantor articles with full content for the given date.

    Parameters
    ----------
    date_str: str
        Target date in YYYY-MM-DD format.
    max_articles: int
        Maximum number of articles to scrape.
    delay: float
        Delay between requests in seconds.

    Returns
    -------
    List[Dict[str, Optional[str]]]
        List of article dictionaries with full content.
    """
    xml = fetch_news_sitemap()
    if not xml:
        return []
    
    # Get basic article info from sitemap
    sitemap_articles = parse_news_sitemap(xml, date_str)
    
    if len(sitemap_articles) > max_articles:
        sitemap_articles = sitemap_articles[:max_articles]
    
    # Fetch full content for each article
    full_articles = []
    for sitemap_article in sitemap_articles:
        article = parse_article(sitemap_article["url"])
        if article and article.get("title"):
            # Use sitemap title if article parsing didn't get one
            if not article["title"]:
                article["title"] = sitemap_article["title"]
            # Use sitemap category
            article["category"] = sitemap_article["category"]
            full_articles.append(article)
        time.sleep(delay)
    
    return full_articles


def format_articles_as_string(articles: List[Dict[str, Optional[str]]], date_str: str) -> str:
    """Format scraped articles as a readable string."""
    formatted_text = []
    
    # Add header
    header = f"""JUGANTOR NEWS SCRAPER
Date: {date_str}
Total Articles: {len(articles)}
Scraped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{' ' * 100}

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
        authors = article.get("authors") or "Unknown Author"
        
        formatted_text.append(f"Category: {category}")
        formatted_text.append(f"Date: {date_published}")
        formatted_text.append(f"Author(s): {authors}")
        formatted_text.append("")
        
        # Add news content
        body = article.get("body") or "No content available"
        formatted_text.append("NEWS CONTENT:")
        formatted_text.append(" " * 50)
        formatted_text.append(body)
        formatted_text.append("")
        formatted_text.append(" " * 50)
        formatted_text.append("")
        formatted_text.append("")
    
    return "\n".join(formatted_text)


def main() -> None:
    headlines = get_jugantor_headlines(max_articles=10)
    # Always save a file, even if empty
    save_headlines_to_file(headlines)


if __name__ == "__main__":
    main()