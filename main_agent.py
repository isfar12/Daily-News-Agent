from news_list_graph import get_news_list
from chosen_article_graph import get_specific_article
from prompt import news_chat_prompt
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import START, MessagesState, StateGraph,END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import ToolMessage
from pathlib import Path
from llm import llm

load_dotenv()

THREAD_ID = "session-fresh"  # define a constant for the thread id
db_path = Path("chat_history_checkpoints.db")

tools=[get_news_list,get_specific_article]

llm_with_tools =llm.bind_tools(tools)



def call_model(state: MessagesState):
    # Pass all messages to maintain conversation context
    formatted_messages = news_chat_prompt.invoke({"input": state["messages"][-1].content}).to_messages()
    
    # Replace the human message with the full conversation context
    formatted_messages = formatted_messages[:-1] + state["messages"]
    
    # Get thread_id from state if available
    thread_id = state.get("thread_id", THREAD_ID)
    
    # First try with simple LLM to see if it's a greeting/conversation
    last_user_message = state["messages"][-1].content.lower() if state["messages"] else ""
    
    # Check if it's clearly a news request
    news_keywords = ["news", "headlines", "breaking", "article", "latest", "today's news", "sports news", "politics news"]
    is_news_request = any(keyword in last_user_message for keyword in news_keywords)
    
    if is_news_request:
        # Use LLM with tools for news requests
        response = llm_with_tools.invoke(formatted_messages)
        
        # If there are tool calls, execute them
        if hasattr(response, 'tool_calls') and response.tool_calls:
            
            tool_messages = []
            
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                # Add thread_id to tool arguments
                tool_args['thread_id'] = thread_id
                
                try:
                    if tool_name == 'get_news_list':
                        result = get_news_list.invoke(tool_args)
                    elif tool_name == 'get_specific_article':
                        result = get_specific_article.invoke(tool_args)
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
            
            # Get final response with tool results
            final_messages = formatted_messages + [response] + tool_messages
            final_response = llm.invoke(final_messages)
            return {"messages": final_response}
    else:
        # Use simple LLM for conversations/greetings
        response = llm.invoke(formatted_messages)
    
    return {"messages": response}

workflow = StateGraph(state_schema=MessagesState)
workflow.add_node("call_model", call_model)

workflow.add_edge(START, "call_model")
workflow.add_edge("call_model",END)

def process_chat_query(query, thread_id=None):
    """Function to process a chat query, invoke the model, and save the state."""
    if thread_id is None:
        thread_id = THREAD_ID
    
    with SqliteSaver.from_conn_string(str(db_path)) as cp:
        cp.setup()
        config = {"configurable": {"thread_id": thread_id}}
        compiled_app = workflow.compile(checkpointer=cp)
        try:
            current_state = compiled_app.get_state(config)
            if current_state and current_state.values.get("messages"):
                existing_messages = current_state.values["messages"]
            else:
                existing_messages = []
        except:
            existing_messages = []
        
        # Add new message to existing conversation
        new_messages = existing_messages + [HumanMessage(query)]
        output = compiled_app.invoke({"messages": new_messages, "thread_id": thread_id}, config)
        
        output["messages"][-1].pretty_print()
         
        return output

if __name__ == "__main__":
    # Example usage with custom thread IDs
    user_thread = "user-demo-123"
    
    process_chat_query("What is today top 10 news?", thread_id=user_thread)
    process_chat_query("Can you tell me more about 5th News Article?", thread_id=user_thread)
    process_chat_query("Hi! I'm Bob.", thread_id=user_thread)
    process_chat_query("What's my name?", thread_id=user_thread)
    process_chat_query("What was the last news you explained?", thread_id=user_thread)