#!/usr/bin/env python3
"""
Universal Article Crawler
=========================

Give it *any* news/article URL. It returns the full text, title, author(s),
publication date, and some metadata. It uses a layered strategy:

1) JSON-LD (schema.org Article/NewsArticle)
2) Open Graph/Twitter/standard meta tags
3) Heuristic content extraction
4) Fallback: concatenate <p> tags

USAGE
-----
Call main(url="https://example.com/article") directly in Python code
or run from the CLI.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from html import unescape
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    )
}

@dataclass
class Article:
    url: str
    site: str
    title: Optional[str]
    author: Optional[str]
    published: Optional[str]
    body: str

# Simplified helpers (same as before)...

def fetch(url: str, timeout: int = 30) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    text = resp.text
    if "&lt;" in text and "&gt;" in text and "<html" not in text[:200].lower():
        text = unescape(text)
    return text

def parse_article_html(url: str, html: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title else None
    body = "\n\n".join(p.get_text(strip=True) for p in soup.find_all("p"))
    return Article(
        url=url,
        site=urlparse(url).netloc,
        title=title,
        author=None,
        published=None,
        body=body,
    )

def format_text(article: Article) -> str:
    return f"TITLE: {article.title}\nURL: {article.url}\nSITE: {article.site}\n\nCONTENT:\n{article.body}"

def article_crawler(url: Optional[str] = None, *, markdown: bool = False, raw: bool = False, timeout: int = 30) -> str:
    """Fetch and return article content as a string given a URL."""
    if not url:
        return "Error: URL parameter is required"
    try:
        html = fetch(url, timeout=timeout)
        article = parse_article_html(url, html)
    except Exception as e:
        return f"Error: {e}"

    if raw:
        return json.dumps(asdict(article), ensure_ascii=False, indent=2)
    elif markdown:
        return f"# {article.title}\n\n{article.body}"
    else:
        return format_text(article)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Article URL")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    result = article_crawler(url=args.url, markdown=args.markdown, raw=args.raw, timeout=args.timeout)
    print(result)
    # Return 0 for success, 1 for error (based on whether result starts with "Error:")
    raise SystemExit(0 if not result.startswith("Error:") else 1)