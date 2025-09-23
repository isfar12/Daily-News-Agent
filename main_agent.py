from news_list_graph import get_news_list
from chosen_article_graph import get_specific_article
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate

from dotenv import load_dotenv
load_dotenv()

llm=ChatOllama(model="llama3.2:latest", temperature=0.7, max_tokens=32000)

tools=[get_news_list,get_specific_article]

# Create a system prompt to guide tool usage
system_prompt = """You are a helpful news assistant. You have access to tools for getting news information.

CRITICAL GUIDELINES:
- ONLY use tools when the user specifically asks for news, articles, or current events
- For greetings (hello, hi, how are you), general conversation, or non-news questions, respond directly WITHOUT using any tools

TOOL SELECTION RULES:
- Use get_news_list for ALL news requests (general, category-specific, or topic-specific)
  Examples: "latest news", "today's news", "sports news", "politics news", "business news", "technology news"
- Use get_specific_article for SPECIFIC article requests by number/position 
  Examples: "3rd article", "first article", "6th news", "number 5 article", "article 2", "6 number news"

SPECIFIC ARTICLE INDICATORS:
- Numbers: 1st, 2nd, 3rd, 4th, 5th, 6th, first, second, third, fourth, fifth, sixth
- Patterns: "number X", "article X", "X news", "X number news"

Examples:
- "Hello" or "How are you?" -> Respond directly, DO NOT use tools
- "What's the latest news?" -> Use get_news_list
- "Show me sports news" -> Use get_news_list
- "Tell me about politics news" -> Use get_news_list
- "Business news today" -> Use get_news_list
- "Technology updates" -> Use get_news_list
- "Tell me about the 3rd article" -> Use get_specific_article
- "I want to know about the 6 number news" -> Use get_specific_article
- "Show me article 2" -> Use get_specific_article
- "What's the first news?" -> Use get_specific_article
- "Thanks" or "Good morning" -> Respond directly, DO NOT use tools

If the user is NOT asking for news or articles, just have a normal conversation without tools."""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}")
])

# Create the chain with prompt
llm_with_tools = prompt | llm.bind_tools(tools)
response=llm_with_tools.invoke({"input": "What's the latest news?"})

# Check if LLM wants to call tools
if hasattr(response, 'tool_calls') and response.tool_calls:
    print("=== TOOLS THAT WOULD BE INVOKED ===")
    for i, tool_call in enumerate(response.tool_calls, 1):
        print(f"{i}. Tool: {tool_call['name']}")
        print(f"   Arguments: {tool_call['args']}")
        print(f"   ID: {tool_call['id']}")
        print()
else:
    print("No tools would be invoked")
    print(f"Direct response: {response.content}")

print(f"Full response: {response}")

# Alternative method: Create a function to analyze tool calls
def analyze_tool_calls(user_input: str):
    """Analyze what tools would be called without executing them"""
    response = llm_with_tools.invoke({"input": user_input})
    
    print(f"\n=== ANALYSIS FOR: '{user_input}' ===")
    
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"🔧 {len(response.tool_calls)} tool(s) would be invoked:")
        for i, tool_call in enumerate(response.tool_calls, 1):
            print(f"   {i}. {tool_call['name']}({tool_call['args']})")
    else:
        print("💬 No tools - direct LLM response")
        if hasattr(response, 'content') and response.content:
            print(f"   Response: {response.content}")
    
    return response

# Test with different inputs
test_inputs = [
    "What's the latest news?",
    "Tell me about the 3rd article", 
    "Hello, how are you?",
    "Show me sports news",
    "Politics news today",
    "Explain the first article in detail",
    "I want to know about the 6 number news"
]

for test_input in test_inputs:
    analyze_tool_calls(test_input)