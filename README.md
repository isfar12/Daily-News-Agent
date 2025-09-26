# Daily News Agent

A multi-agent, multilingual news intelligence app built with Streamlit, LangGraph, and LLM-powered tools. Designed for robust, production-style news scraping, querying, and article analysis in both Bangla and English.

## Features

- **Multi-user session support**: Thread-scoped conversation state, no global variables
- **LangGraph workflow orchestration**: Modular graphs for news listing and article selection, with SQLite checkpointing
- **Tool-based LLM integration**:
  - `get_news_list`: Fetches dynamic top-N headlines (supports words, digits, ordinals)
  - `get_specific_article`: Selects and retrieves full content for a specific article
- **Universal Article Crawler**:
  - Heuristic extraction for any news site
  - Site-specific post-processing (Daily Star: removes sidebar; Dhaka Tribune: strips duplicate summary)
- **Bangla-first content integrity**: No forced translation, full narrative and quotes preserved
- **Structured LLM outputs**: Safer parsing, fallback guards for malformed results
- **Clean chat history export**: Only user and assistant messages, tool chatter excluded

## How It Works

1. **User asks**: "Top 12 headlines", "Explain 5th article", "More about number 3", "Give me the last sports news"
2. **LangGraph orchestrates**: Decides which tool to call based on query type
3. **Tools extract**: News list or specific article, using robust number extraction (ordinals, words, digits, fallback)
4. **Crawler fetches**: Full article content, applies site-specific cleanup
5. **Response returned**: Preserves original language, full content, and context

## Stack

- Python 3.11+
- Streamlit (UI)
- LangChain + LangGraph (agent orchestration)
- Groq-hosted Llama 3.1 (LLM)
- BeautifulSoup (content extraction)
- SQLite (state/checkpoint persistence)
- Pydantic (structured outputs)

## Architecture & Flow

### High-Level Component Flow

```mermaid
flowchart LR
    A[👤 User Query] --> B[🤖 Main Agent]
    
    B -->|"Today's news"<br/>"Top 10 headlines"| C[📰 News List Tool]
    B -->|"Explain 3rd article"<br/>"Tell me about #5"| D[📄 Article Tool]
    
    C --> E[📊 News Sources<br/>Daily Star, Dhaka Tribune<br/>Prothom Alo, Jugantor]
    
    D --> F[🔍 Article Crawler]
    F --> E
    
    C --> G[📋 Headlines List]
    F --> H[📖 Full Article Content]
    
    G --> I[✨ Response<br/>Bangla/English Preserved]
    H --> I
    
    I --> A
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#e8f5e8
    style I fill:#fff3e0
```### Sequence (Example: "Explain the 5th article")

```mermaid
sequenceDiagram
   participant User
   participant UI as Streamlit UI
   participant Agent as MainAgent
   participant ListTool as get_news_list
   participant ArticleTool as get_specific_article
   participant Crawler
   participant Site

   User->>UI: "Explain the 5th article"
   UI->>Agent: query
   alt Headlines not cached
      Agent->>ListTool: fetch headlines
      ListTool-->>Agent: top N headlines
   end
   Agent->>ArticleTool: article_number=5
   ArticleTool->>Crawler: fetch URL
   Crawler->>Site: HTTP GET
   Site-->>Crawler: HTML
   Crawler-->>ArticleTool: cleaned full content
   ArticleTool-->>Agent: article text
   Agent-->>UI: formatted response
   UI-->>User: Full article (Bangla preserved)
```

### Key Responsibilities

| Component | Responsibility |
|-----------|----------------|
| Main Agent (`main_agent.py`) | Classifies intent & routes to tools |
| News List Graph | Produces cached headline list (top N logic) |
| Chosen Article Graph | Resolves article number -> URL -> full content |
| Universal Crawler | Fetches & cleans article (site-specific rules) |
| SQLite Checkpoints | Persist conversation & tool state |

If Mermaid diagrams do not render (e.g. some IDEs), view the README directly on GitHub or use an online Mermaid renderer.

## Setup & Run

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Start the app**:
   ```bash
   streamlit run streamlit_app.py
   ```
3. **Test the crawler**:
   ```bash
   python test_crawler.py
   ```

## Key Files

- `main_agent.py`: Orchestrates user queries, tool calls, and session state
- `news_list_graph.py`: Handles news list extraction and top-N logic
- `chosen_article_graph.py`: Handles specific article selection and retrieval
- `agent.py`: Defines all tools and extraction logic
- `crawler/universal_article_crawler.py`: Universal news/article content extraction
- `test_crawler.py`: CLI test harness for the crawler
- `.gitignore`: Ignores checkpoint binaries and cache files

## Customization

- **Add new sites**: Extend the crawler with new post-processing rules
- **Improve Bangla support**: Tune prompts and fallback logic for richer responses
- **Integrate more tools**: Add summarization, sentiment, or clustering tools

## Example Queries

- "Show me the top 15 news headlines"
- "Explain the 3rd article in detail"
- "More about number 10"
- "Give me the last sports news"

## Responsible Engineering

- No API keys or secrets stored in code
- Tool responses validated before use
- Defensive guards for empty or malformed LLM outputs

## License

MIT

---

For questions, collaboration, or feedback, connect via LinkedIn or GitHub!
