"""
dhaka_tribune_scraper.py
========================

This script provides a simple example of how to extract the latest news
articles from the Dhaka Tribune website while respecting the site's
robots.txt directives.  It reads the ``news-sitemap.xml`` published by
Dhaka Tribune, extracts a configurable number of the most recent
article URLs, fetches each article, and parses out key details such as
the title, author, publication date, and the full body text.

Key design points
-----------------

* **Respect for robots.txt** – The script fetches only the public
  sitemap and a limited number of articles.  It avoids any URLs
  explicitly disallowed in the robots file (e.g. ``/cgi-bin/``,
  ``/cdn-cgi/``, ``/register/``, ``/login/``, or ``/api/``).  Before
  running the script at scale, you should always review the site's
  terms of service and robots file to ensure compliance.

* **Modular functions** – The script is broken into smaller functions
  (``get_latest_article_urls`` and ``parse_article``) to make it easy to
  test and reuse pieces of the logic.  Each function has a clear
  responsibility.

* **Timezone handling** – Publication dates are exposed in ISO 8601
  format with a timezone offset.  The script converts these to a
  timezone-aware ``datetime`` in the ``Asia/Dhaka`` timezone using
  Python 3.9’s ``zoneinfo`` module.  This ensures dates are presented
  in a consistent local time for users in Bangladesh.

* **CSV output** – For demonstration purposes the script writes its
  results to ``dhaka_tribune_articles.csv`` in the working directory.
  Each row contains the URL, title, author, publication date (in
  ISO 8601 format), and the article body.  You can adapt the output
  format to your needs (e.g. JSON, database storage, etc.).

Usage example
-------------

Run the script from the command line.  By default it will fetch the
five most recent articles listed in the sitemap:

.. code:: bash

   python3 dhaka_tribune_scraper.py

You can change the number of articles scraped by passing the
``--limit`` argument:

.. code:: bash

   python3 dhaka_tribune_scraper.py --limit 10

Note that scraping websites can place load on the remote server.  Use
the ``--limit`` parameter responsibly to avoid over‑loading the site.
Always double‑check the site’s terms and robots policy before
scraping beyond a few articles.
"""

import argparse
import csv
import sys
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

try:
    # Python 3.9+: zoneinfo is available in the standard library.
    from zoneinfo import ZoneInfo
except ImportError:
    # For Python versions <3.9, fall back to pytz if available.  The
    # script explicitly prefers the standard library when possible.
    try:
        from pytz import timezone as ZoneInfo  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Timezone support requires Python 3.9+ or the pytz package"
        ) from exc


SITEMAP_URL = "https://www.dhakatribune.com/news-sitemap.xml"


@dataclass
class Article:
    """Container for article metadata and content."""

    url: str
    title: str
    author: Optional[str]
    publication_date: Optional[str]
    content: str


def get_latest_article_urls(limit: int) -> List[str]:
    """Retrieve the most recent article URLs from the Dhaka Tribune news sitemap.

    Parameters
    ----------
    limit:
        The maximum number of article URLs to return.

    Returns
    -------
    List[str]
        A list of article URLs, in the order they appear in the sitemap.
    """
    # Use a custom User-Agent header to mimic a standard browser.  Some
    # sites return 403 errors to unknown clients.  The string below is
    # intentionally generic and does not identify a specific user.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(SITEMAP_URL, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        print(f"Error fetching sitemap: {exc}", file=sys.stderr)
        return []

    # Parse the XML.  The sitemap uses the standard sitemap namespace.
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        print(f"Failed to parse sitemap XML: {exc}", file=sys.stderr)
        return []

    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: List[str] = []

    for url_elem in root.findall("ns:url", ns):
        loc_elem = url_elem.find("ns:loc", ns)
        if loc_elem is not None and loc_elem.text:
            loc_text = loc_elem.text.strip()
            # Basic check to avoid disallowed paths (as per robots.txt)
            if any(
                loc_text.startswith(f"https://www.dhakatribune.com{path}")
                for path in ["/cgi-bin/", "/cdn-cgi/", "/register/", "/login", "/api/"]
            ):
                continue
            urls.append(loc_text)
            if len(urls) >= limit:
                break
    return urls


def parse_article(url: str) -> Article:
    """Download and parse a Dhaka Tribune article.

    This function extracts the title, author, publication date, and full
    text content from the specified article URL.  It relies on the
    structure observed in Dhaka Tribune’s HTML, where the headline
    appears in an ``<h1>`` with class ``title``, the author in a
    ``<span>`` with class ``name``, the publication timestamp in a
    ``<span>`` with class ``published_time`` (using the ISO timestamp
    stored in the ``content`` attribute), and the article body inside
    a ``<div>`` with ``itemprop="articleBody"``.

    Parameters
    ----------
    url:
        The URL of the article to parse.

    Returns
    -------
    Article
        A dataclass instance containing the parsed article data.
    """
    # Use the same User-Agent as sitemap fetch to reduce the chance of
    # receiving a 403 Forbidden response.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch article {url}: {exc}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract the headline
    title_elem = soup.find("h1", class_="title")
    title = title_elem.get_text(strip=True) if title_elem else ""

    # Extract the author name
    author_elem = soup.find("span", class_="name")
    author = author_elem.get_text(strip=True) if author_elem else None

    # Extract publication time as ISO string, then convert to local timezone
    published_span = soup.find("span", class_="published_time")
    publication_date: Optional[str] = None
    if published_span:
        iso_time = published_span.get("content")
        if iso_time:
            try:
                dt_utc = datetime.fromisoformat(iso_time)
                # Convert to Asia/Dhaka timezone
                dt_local = dt_utc.astimezone(ZoneInfo("Asia/Dhaka"))
                publication_date = dt_local.isoformat()
            except ValueError:
                # Fall back to storing the raw ISO string
                publication_date = iso_time

    # Extract article paragraphs
    body_div = soup.find("div", itemprop="articleBody")
    paragraphs: List[str] = []
    if body_div:
        for p in body_div.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)
    content = "\n\n".join(paragraphs)

    return Article(
        url=url,
        title=title,
        author=author,
        publication_date=publication_date,
        content=content,
    )


def get_dhaka_tribune_headlines(max_articles: int = 10) -> List[dict]:
    """
    Get Dhaka Tribune headlines (URL and title only) for today's date.
    
    Parameters
    ----------
    max_articles : int, optional
        Maximum number of articles to return. Default is 10.
    
    Returns
    -------
    List[dict]
        List of dictionaries with 'url', 'title', 'author', and 'publication_date' keys.
    """
    urls = get_latest_article_urls(limit=max_articles)
    if not urls:
        return []

    headlines = []
    for url in urls:
        try:
            article = parse_article(url)
            headlines.append({
                "url": article.url,
                "title": article.title,
                "author": article.author or "Unknown",
                "publication_date": article.publication_date or "Unknown"
            })
        except Exception:
            continue
    
    return headlines


def save_headlines_to_file(headlines: List[dict]) -> None:
    """
    Save only URL and title to a text file in news folder.
    
    Parameters
    ----------
    headlines : List[dict]
        List of headline dictionaries
    """
    # Get today's date automatically
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Always save to the project-root news folder (independent of CWD)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_dir = os.path.join(project_root, "news")
    os.makedirs(news_dir, exist_ok=True)
    filename = os.path.join(news_dir, f"dhaka_tribune_headlines_{date_str}.txt")
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("DHAKA TRIBUNE HEADLINES\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Total Headlines: {len(headlines)}\n")
            f.write(f"Scraped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(" " * 80 + "\n\n")
            
            for i, article in enumerate(headlines, 1):
                f.write(f"{i:3d}. {article['title']}\n")
                f.write(f"     URL: {article['url']}\n")
                f.write(f"     Author: {article['author']}\n")
                f.write(f"     Published: {article['publication_date']}\n\n")
    except Exception as e:
        pass


def write_txt(filename: str, articles: Iterable[Article]) -> None:
    """Write a sequence of Article objects to a txt file in the news folder.

    Parameters
    ----------
    filename:
        The path of the txt file to create.
    articles:
        An iterable of ``Article`` objects.
    """
    # Always save to the project-root news folder (independent of CWD)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_dir = os.path.join(project_root, "news")
    os.makedirs(news_dir, exist_ok=True)
    # Get today's date for filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    full_filename = os.path.join(news_dir, f"dhaka_tribune_headlines_{date_str}.txt")
    
    articles_list = list(articles)
    
    try:
        with open(full_filename, "w", encoding="utf-8") as f:
            f.write("DHAKA TRIBUNE HEADLINES\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Total Headlines: {len(articles_list)}\n")
            f.write(f"Scraped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(" " * 80 + "\n\n")
            
            for i, article in enumerate(articles_list, 1):
                f.write(f"{i:3d}. {article.title}\n")
                f.write(f"     URL: {article.url}\n")
                if article.author:
                    f.write(f"     Author: {article.author}\n")
                if article.publication_date:
                    f.write(f"     Published: {article.publication_date}\n")
                f.write("\n")
    except Exception as e:
        pass


def write_csv(filename: str, articles: Iterable[Article]) -> None:
    """Write a sequence of Article objects to a CSV file.

    Parameters
    ----------
    filename:
        The path of the CSV file to create.
    articles:
        An iterable of ``Article`` objects.
    """
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "title", "author", "publication_date", "content"])
        for article in articles:
            writer.writerow([
                article.url,
                article.title,
                article.author if article.author else "",
                article.publication_date if article.publication_date else "",
                article.content,
            ])


def main(argv: Optional[List[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Scrape recent articles from Dhaka Tribune.")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of recent articles to scrape from the sitemap (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dhaka_tribune_headlines.txt",
        help="Output txt filename (default: dhaka_tribune_headlines.txt)",
    )
    args = parser.parse_args(argv)

    urls = get_latest_article_urls(limit=args.limit)
    if not urls:
        return 1

    articles: List[Article] = []
    for url in urls:
        try:
            article = parse_article(url)
            articles.append(article)
        except Exception as exc:
            # Log failure but continue with next article
            continue

    write_txt(args.output, articles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())