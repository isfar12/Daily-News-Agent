from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph,START,END
from typing import Annotated,TypedDict
from langchain.tools import tool
from pydantic import BaseModel, Field
from agent import news_list_tool
from llm import llm
from dotenv import load_dotenv
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver

THREAD_ID = "session-1"  # define a constant for the thread id
NEWS_STATE_KEY = "news_list_graph"  # define a constant for the state key

db_path = Path("chosen_news_list_checkpoints.db")
load_dotenv()

#------------------------ CLASS DEFINITIONS ------------------------#

class ArticleGraph(TypedDict):
    input: Annotated[str, Field(description="The user input for the article search")]
    top_n: Annotated[int, Field(description="The number of top news articles to fetch")]
    news_list: Annotated[str, Field(description="A list of news article containing titles , categories and urls")]

class N_Number(BaseModel):
    number: str = Field(description="The number extracted from the text.")

#------------------------ FUNCTION DEFINITIONS ------------------------#

# llm=ChatOllama(model="gemma3:4b", temperature=0.3, max_tokens=1000)


n_number_finder=llm.with_structured_output(N_Number)


def news_list_function(state: ArticleGraph) -> ArticleGraph:
    """Single function to handle both general and specific topic news requests"""
    news_list = news_list_tool.invoke({"top_n": str(state["top_n"]), "query": state["input"]})
    return {
        "news_list": news_list
    }

#------------------------ GRAPH DEFINITIONS ------------------------#
news_list_graph=StateGraph(ArticleGraph)
news_list_graph.add_node("news_list_function",news_list_function)

news_list_graph.add_edge(START,"news_list_function")
news_list_graph.add_edge("news_list_function",END)



def get_news_list_state(thread_id: str = None):
    if thread_id is None:
        thread_id = THREAD_ID
        
    with SqliteSaver.from_conn_string(str(db_path)) as cp:
        print("Fetching news list state...")
        cfg = {"configurable": {"thread_id": thread_id, "state_key": NEWS_STATE_KEY}}
        compiled = news_list_graph.compile(checkpointer=cp)  # Compile the graph
        
        # Access the state and retrieve the 'news_list'
        state_data = compiled.get_state(cfg)
        articles = state_data.values["news_list"]
    return articles


@tool
def n_news(user_input: str):
    '''This function determines the number of news articles to fetch based on user input.
    If no number is mentioned, it defaults to 10.
    Examples:
    If user asks: Show me the top 5 news articles.
    Your answer should be: 5 (Only the number)
    user: Show me fifth news article.
    Answer: 5
    user: I want to read some news.
    Answer: 10
    '''
    prompt=PromptTemplate(
        input_variables=["user_input"],
        template='''From the users query: {user_input},
         
           Find out the number from the text. If no number is mentioned, return 10. else return the number mentioned in the query or try to understand from the query and return that number only
           
           Examples:
           If user asks: Show me the top 5 news articles.
           Ur answer should be: 5 (Only the number)
           user: Show me fifth news article.
            Answer: 5
           user: I want to read some news.
           Answer: 10
           '''
    )
    n_news=n_number_finder.invoke(prompt.format(user_input=user_input)).number
    return n_news

# print(n_news.invoke("today top eight news"))

@tool
def get_news_list(user_input: str, thread_id: str = None):
    """Get today's latest news headlines with urls. Handles both general and specific topic requests.
    
   
    Do NOT use for greetings or general conversation.
    """
    if thread_id is None:
        thread_id = THREAD_ID
        
    with SqliteSaver.from_conn_string(str(db_path)) as cp:
        cp.setup()
        graph = news_list_graph.compile(checkpointer=cp)

        cfg = {"configurable": {"thread_id": thread_id,"state_key": NEWS_STATE_KEY}}

        top_n=n_news.invoke({"user_input": user_input})

        top_n=int(top_n) if top_n.isdigit() else 10
        print("Determined top_n:", top_n)
        print("Invoking get_news_list with input and top_n...")
        graph.invoke({"input": user_input, "top_n": top_n}, config=cfg)
        result=graph.get_state(cfg).values.get("news_list")
    return result

# print(result)