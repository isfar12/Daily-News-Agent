from langgraph.graph import StateGraph, START, END
from typing import Annotated, TypedDict
from pydantic import Field
from agent import news_explainer_tool, article_chooser_tool
from dotenv import load_dotenv
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from news_list_graph import THREAD_ID, get_news_list,get_news_list_state
from langchain.tools import tool

db_path = Path("chosen_article_checkpoints.db") 
news_list_db_path = Path("news_list_checkpoints.db")
load_dotenv()

THREAD_ID = "session-1"  # define a constant for the thread id
STATE_KEY = "chosen_article_graph"  # define a constant for the state key



class ChosenArticleGraph(TypedDict):
    user_input: Annotated[str, Field(description="The user input for the article search")]
    url: Annotated[str, Field(description="The chosen article url based on the user input")]

def chosen_article_url(state: ChosenArticleGraph) -> ChosenArticleGraph:
    ''' This function chooses an article URL based on user input and a list of articles. '''
    user_input = state["user_input"]
    # Read the previously computed news list from the news_list_graph checkpoint
    articles = get_news_list_state()
    # print(articles)
    if not articles:
        try:
            articles = get_news_list("today news", top_n=10)
        except Exception:
            articles = ""

    chosen = article_chooser_tool.invoke({"user_input": user_input, "articles": articles})
    return {
        "user_input": user_input,
        "url": chosen.url
    }


graph=StateGraph(ChosenArticleGraph)
graph.add_node("chosen_article_url",chosen_article_url)

graph.add_edge(START,"chosen_article_url")
graph.add_edge("chosen_article_url",END)

config = {"configurable": {"thread_id": THREAD_ID, "state_key": STATE_KEY}}

@tool
def get_specific_article(user_input: str):
    """Get detailed information about a specific article when user mentions article numbers, positions, or wants details about a particular article.
        
        Args:
            user_input: User's request for a specific article (e.g., 'tell me about the 3rd article', 'explain the first article')
            
        Examples of when to use:
        - "Tell me about the 3rd article"
        - "Explain the first article in detail"
        - "What's the 5th news item about?"
        
        Do NOT use for general news requests.
        """
    with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        workflow = graph.compile(checkpointer=checkpointer)
        result = workflow.invoke({"user_input": user_input}, config=config)
        print("selected url:", result)
    if isinstance(result, dict):
        result_news= news_explainer_tool.invoke(result).content
        print("news explained.")
    return result_news



# news=get_specific_article("Tell me about the sports article.")
# print(news)