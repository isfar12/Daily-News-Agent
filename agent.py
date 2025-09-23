from langchain_ollama import ChatOllama
from langchain_community.document_loaders import TextLoader
from core.loaders import load_news_articles
from core.scraper_loaders import run_all_scrapers
from core.universal_article_crawler import article_crawler
from core.parser import NewsSummary,UrlOnly
from langchain.tools import tool
from core.scraper_loaders import run_all_scrapers
from core.loaders import load_news_articles
from core.universal_article_crawler import article_crawler
from prompt import news_list_prompt,news_explainer_prompt,article_choose_tool_prompt


llm=ChatOllama(model="gemma3:4b", temperature=0.7, max_tokens=32000)
llm_url_only=llm.with_structured_output(UrlOnly)

@tool
def news_list_tool(top_n: str, query: str = "latest news") -> str:
    """Given a list of news articles, return the top news headlines,category/section with their urls in markdown format.
    Can handle both general and specific topic requests."""
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
def news_explainer_tool(url: str) -> NewsSummary:
    """ Given a news article url, return the explained news article with title, content and url."""
    article = article_crawler(url)
    prompt=news_explainer_prompt.format(article=article)
    explained_article = llm.invoke(prompt)
    return explained_article

@tool
def article_chooser_tool(user_input: str, articles: str) -> str:
    """ Given a user input and a list of articles, choose the article that matches the user input and return its url."""
    prompt=article_choose_tool_prompt.format(user_input=user_input, articles=articles)
    chosen_article_url = llm_url_only.invoke(prompt)
    return chosen_article_url
