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
    thread_id: Annotated[str, Field(description="Thread ID for conversation context", default=THREAD_ID)]

def chosen_article_url(state: ChosenArticleGraph) -> ChosenArticleGraph:
    ''' This function chooses an article URL based on user input and a list of articles. '''
    user_input = state["user_input"]
    thread_id = state.get("thread_id", THREAD_ID)
    
    articles = get_news_list_state(thread_id)
    # print(articles)
    if not articles:
        try:
            articles = get_news_list("today news", thread_id=thread_id, top_n=10)
        except Exception:
            articles = ""

    chosen = article_chooser_tool.invoke({"user_input": user_input, "articles": articles})
    return {
        "user_input": user_input,
        "url": chosen.url,
        "thread_id": thread_id
    }


graph=StateGraph(ChosenArticleGraph)
graph.add_node("chosen_article_url",chosen_article_url)

graph.add_edge(START,"chosen_article_url")
graph.add_edge("chosen_article_url",END)



@tool
def get_specific_article(user_input: str, thread_id: str = None):
    """Get full content of a specific article. Use when user asks about a particular article by number or position.
    
    Use for: "1st article", "tell me about 3rd news", "explain the fifth one", "number 10 article"
    Don't use for: general news requests or getting news lists
    """
    if thread_id is None:
        thread_id = THREAD_ID
        
    config = {"configurable": {"thread_id": thread_id, "state_key": STATE_KEY}}
    
    with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        workflow = graph.compile(checkpointer=checkpointer)
        result = workflow.invoke({"user_input": user_input, "thread_id": thread_id}, config=config)
        # print("selected url:", result)
    if isinstance(result, dict):
        result_news= news_explainer_tool.invoke(result)
        # print("raw article content fetched.")
    return result_news



# news=get_specific_article("Tell me about the sports article.")
# result=get_specific_article.invoke({"user_input": "Explain number 2 article", "thread_id": "test-thread"})
# print(result)