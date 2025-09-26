from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# Main LLM configuration
llm = ChatOllama(
    model="llama3.1:8b", #llama3.1:8b 
    # num_thread=10,
    temperature=0.4, 
    top_p=.5,
    num_ctx=32768  # Set context window to 32k tokens
)

# Alternative LLM (commented out)
# llm = ChatGroq(
#     model="llama-3.1-8b-instant",
#     temperature=0.5,
# )