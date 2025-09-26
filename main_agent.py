from news_list_graph import get_news_list
from chosen_article_graph import get_specific_article
from prompt import news_chat_prompt
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import START, MessagesState, StateGraph,END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import ToolMessage
from pathlib import Path
from llm import llm
from langchain_groq import ChatGroq

load_dotenv()

THREAD_ID = "session-fresh"  # define a constant for the thread id
db_path = Path("chat_history_checkpoints.db")

tools=[get_news_list,get_specific_article]

# Alternative LLM (Testing output)
# llm = ChatGroq(
#     model="llama-3.1-8b-instant",
#     temperature=0.5,
# )
llm_with_tools =llm.bind_tools(tools)


def call_model(state: MessagesState, config=None):
    # this will return the previous final state messages + new user message
    formatted_messages = news_chat_prompt.invoke({"input": state["messages"][-1].content}).to_messages()
    formatted_messages = formatted_messages[:-1] + state["messages"]
    
    # we need the original user message to determine if it's a news request
    original_user_message = state["messages"][-1].content if state["messages"] else ""
    
    # Extract thread_id from config (this is the proper LangGraph way)
    thread_id = config.get("configurable", {}).get("thread_id", THREAD_ID) if config else THREAD_ID
    
    # Check if it's clearly a news request
    news_keywords = ["news","title", "headlines", "breaking", "article", "latest", "today's news", "sports news", "politics news", "tell me about", "explain", "more about", "details about", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th", "13th", "14th", "15th", "16th", "17th", "18th", "19th", "20th", "number", "last", "final", "fast","explain","discuss","describe"]
    is_news_request = any(keyword in original_user_message.lower() for keyword in news_keywords) # returns True or False
    
    if is_news_request:
        # Use LLM with tools for news requests
        response = llm_with_tools.invoke(formatted_messages)
        
        #-----------------TOOL CALLING-------------------------------- 
        if hasattr(response, 'tool_calls') and response.tool_calls:
            
            tool_messages = []
            
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']

                # Add thread_id and user input to tool arguments

                tool_args['thread_id'] = thread_id
                tool_args['user_input'] = original_user_message
                try:
                    if tool_name == 'get_news_list':
                        result = get_news_list.invoke(tool_args) # this will return the news list string
                    elif tool_name == 'get_specific_article':
                        result = get_specific_article.invoke(tool_args) # this will return the article content from internet
                    else:
                        result = f"Unknown tool: {tool_name}"
                    
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id']
                    ))
                except Exception as e:
                    tool_messages.append(ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call['id']
                    ))
            
            final_response=AIMessage(content=str(result)) # i skipped this for now because of poor responses with AI models modified result
            
            # final_messages = formatted_messages + [response] + tool_messages
            # final_response = llm.invoke(final_messages)

            return {"messages": final_response}
    # in this case, it's not a news request, so we will just use regular llm
    else:
        # simple LLM response for conversations/greetings with history included
        response = llm.invoke(formatted_messages)
    
    return {"messages": response}
#------------------- GRAPH DEFINITION -------------------

workflow = StateGraph(state_schema=MessagesState)
workflow.add_node("call_model", call_model)

workflow.add_edge(START, "call_model")
workflow.add_edge("call_model",END)

#---------------- FUNCTION TO PROCESS CHAT QUERY ----------------

def process_chat_query(user_input, thread_id=None):
    """Function to process a chat query, invoke the model, and save the state."""
    if thread_id is None:
        thread_id = THREAD_ID
    # this will save the state
    with SqliteSaver.from_conn_string(str(db_path)) as cp:
        cp.setup()
        config = {"configurable": {"thread_id": thread_id}}
        compiled_app = workflow.compile(checkpointer=cp) 
        try:
            current_state = compiled_app.get_state(config)
            if current_state and current_state.values.get("messages"):
                all_messages = current_state.values["messages"]
                # fetch only ai and human messages
                filtered_messages = [msg for msg in all_messages if isinstance(msg, (HumanMessage, AIMessage))]
            else:
                filtered_messages = []
        except:
            filtered_messages = []
        
        # Add new message to existing conversation
        new_messages = filtered_messages + [HumanMessage(user_input )]
        output = compiled_app.invoke({"messages": new_messages}, config)

        # get the AIMessage content and return to Streamlit        
        if "messages" in output:
            output["messages"] = [msg for msg in output["messages"] if isinstance(msg, (HumanMessage, AIMessage))]
        
        # Skip pretty_print to avoid Streamlit context issues
        # output["messages"][-1].pretty_print()
         
        return output

# if __name__ == "__main__":
#     # Example usage with custom thread IDs
#     user_thread = "user-demo-123"
    
#     process_chat_query("What is today top 10 news?", thread_id=user_thread)
#     process_chat_query("Can you tell me more about 5th News Article?", thread_id=user_thread)
#     process_chat_query("Hi! I'm Bob.", thread_id=user_thread)
#     process_chat_query("What's my name?", thread_id=user_thread)
#     process_chat_query("What was the last news you explained?", thread_id=user_thread)