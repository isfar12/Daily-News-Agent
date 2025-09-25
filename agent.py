from core.loaders import load_news_articles
from core.scraper_loaders import run_all_scrapers
from core.universal_article_crawler import article_crawler
from core.parser import UrlOnly
from langchain.tools import tool
from core.scraper_loaders import run_all_scrapers
from core.loaders import load_news_articles
from core.universal_article_crawler import article_crawler
from prompt import news_list_prompt,article_choose_tool_prompt
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from llm import llm
load_dotenv()

llm_url_only=llm.with_structured_output(UrlOnly)

def check_todays_news_files():
    """Check if today's news files already exist in the news folder"""
    today = datetime.now().strftime("%Y-%m-%d")
    news_folder = Path("news")
    
    # Expected file names for today
    expected_files = [
        f"dailystar_headlines_{today}.txt",
        f"dhaka_tribune_headlines_{today}.txt", 
        f"jugantor_headlines_{today}.txt",
        f"prothomalo_headlines_{today}.txt"
    ]
    
    # Check if all files exist
    all_files_exist = all((news_folder / filename).exists() for filename in expected_files)
    
    if all_files_exist:
        print(f"Today's news files ({today}) already exist. Skipping scrapers.")
        return True
    else:
        print(f"Some news files for {today} are missing. Running scrapers...")
        return False

@tool
def news_list_tool(top_n: str, query: str = "latest news") -> str:
    """Given a list of news articles, return the top news headlines,category/section with their urls in markdown format.
    Can handle both general and specific topic requests."""
    
    # Check if today's news files already exist
    if not check_todays_news_files():
        print("Running scrapers...")
        run_all_scrapers()
        print("Scraping done.")
    
    articles = load_news_articles()
    print(f"Loaded articles.")
    prompt=news_list_prompt.format(articles=articles, top_n=top_n, query=query)
    top_news = llm.invoke(prompt).content
    print("Top news fetched.")
    return top_news


@tool
def news_explainer_tool(url: str) -> str:
    """ Given a news article url, return the raw article content without processing."""
    article = article_crawler(url)

    return article

@tool
def article_chooser_tool(user_input: str, articles: str) -> str:
    """ Given a user input and a list of articles, choose the article that matches the user input and return its url."""
    prompt=article_choose_tool_prompt.format(user_input=user_input, articles=articles)
    chosen_article_url = llm_url_only.invoke(prompt)
    return chosen_article_url
