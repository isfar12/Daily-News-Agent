from news_list_graph import get_news_list
from chosen_article_graph import get_specific_article
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from main_agent import system_prompt
load_dotenv()

def process_single_message(user_input):
    """Process a single message and show tool execution or response"""
    
    llm = ChatOllama(model="llama3.2:latest", temperature=0.7, max_tokens=32000)
    tools = [get_news_list, get_specific_article]

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    
    llm_with_tools = prompt | llm.bind_tools(tools)
    
    print(f"INPUT: {user_input}")
    print("=" * 50)
    
    try:
        # Get LLM response with potential tool calls
        response = llm_with_tools.invoke({"input": user_input})
        
        # Check if tools should be called
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                print(f"TOOL EXECUTING: {tool_name}")
                print(f"ARGUMENTS: {tool_args}")
                print("-" * 30)
                
                # Execute the tool
                if tool_name == 'get_news_list':
                    result = get_news_list.invoke(tool_args)
                elif tool_name == 'get_specific_article':
                    result = get_specific_article.invoke(tool_args)
                
                print("RESULT:")
                print(result)
        else:
            print("NO TOOLS EXECUTED")
            print("DIRECT RESPONSE:")
            print(response.content)
            
    except Exception as e:
        print(f"ERROR: {e}")


user_message = "Show me the 4th article"  # Change this line

process_single_message(user_message)