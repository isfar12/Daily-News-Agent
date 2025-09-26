from langchain_core.prompts import PromptTemplate,ChatPromptTemplate


news_list_template = """From the provided news articles, select the top {top_n} titles with their categories and urls.

User Query: "{user_input}"
Articles: {articles}

OUTPUT FORMAT - 
For each article, provide a markdown list. The output should be using number bullets like below:
1. Title: ...
    URL: ...
    Category: ...

Continue until {top_n} articles. 


SELECTION RULES:
- Prioritize the PROTHOM ALO HEADLINES and DAILYSTAR HEADLINES collections
- If user asks for specific topic (sports, politics, business), prioritize those articles
- Otherwise, select the most important articles from all categories/sections
- Include both Bangla and English articles - language doesn't matter
- Extract title, URL, and category/section for each article
- Keep original article titles (don't change Bangla/English)
- If there are less than {top_n} articles, show all available articles
"""

article_number_extraction_template = """
User Input: "{user_input}"

Extract the article number from the user input. Look for numbers, ordinals, or positions mentioned.

EXAMPLES:
- "Explain the number 3 article" → 3
- "tell me about 6th news" → 6
- "explain the first article" → 1
- "number 10 news" → 10
- "second article" → 2
- "tell me more about number 10 news" → 10
- "what's the 5th one about" → 5
- "3rd article" → 3
- "more details" → 1

RULES:
- Look for explicit numbers: "3", "10", "6"
- Look for ordinals: "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th"
- Look for words: "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"
- Look for "number X" patterns
- If no specific number is mentioned, return "1"

Extract the number and return it as a string.
"""

article_choose_prompt = """
Article Number: {article_number}
News list: {articles}

TASK:
Find article number {article_number} in the news list and extract its URL.

RULES:
- Look for the line that starts with "{article_number}." 
- Extract the URL from that specific article
- Return ONLY the URL, nothing else

Example:
If article_number is "5" and you see:
5. Some news title
   URL: https://example.com/news
   Category: sports

Return: https://example.com/news
"""

system_prompt = """You are a professional news assistant fluent in both Bangla and English. You have access to tools for getting news information and can maintain conversations.

LANGUAGE HANDLING (CRITICAL):
- ALWAYS preserve the original language of news content (Bangla/English)
- If news is in Bangla (বাংলা), keep it in Bangla - NEVER translate to English
- When presenting Bangla news, provide comprehensive explanations in Bangla

CONVERSATION HANDLING:
- For greetings like "Hi! I'm Bob", "Hello", "How are you?" -> Respond with normal friendly text
- For general chat -> Respond normally without any tool calls
- Remember previous conversation context and names

NEWS TOOL USAGE (MANDATORY - when user asks for news):
- ALWAYS use get_news_list tool for: "latest news", "today's news", "sports news", "show me news", "top news",etc requests
- ALWAYS use get_specific_article tool for: "3rd article", "first article", "article 2", "explain the 5th news" etc requests
- When tools return content, present it EXACTLY as received - do NOT summarize or shorten it

ARTICLE CONTENT HANDLING (CRITICAL):
- When showing article content, ALWAYS display the COMPLETE article content from tools
- For Bangla articles: Provide detailed explanation, context, and full content in Bangla
- Never shorten or shrink the response - provide comprehensive coverage
- Keep the main theme, all details, quotes, and context intact
- If article is incomplete, fetch full content and provide detailed analysis

RESPONSE QUALITY FOR BANGLA CONTENT:
- Provide rich, detailed responses for Bangla news
- Include context, background information, and comprehensive explanations
- Don't give short, minimal responses for Bangla content
- Elaborate on the significance and implications of the news
- Use proper Bangla formatting and structure

RESPONSE STYLE:
- For Bangla article content: Provide detailed, comprehensive explanations in Bangla
- For English article content: Provide full content as received
- For general conversation: Keep responses concise and focused
- For news lists: Show complete lists as provided by tools

STRICT EXAMPLES:
- "Explain the first article" -> [USE get_specific_article tool, return COMPLETE article with detailed explanation]

NEVER start responses with "there was an error" or similar phrases. Focus on providing rich, detailed content."""

news_chat_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}")
])

news_list_prompt = PromptTemplate(
    input_variables=["articles", "top_n", "user_input"],
    template=news_list_template
)

article_number_extraction_prompt = PromptTemplate(
    input_variables=["user_input"],
    template=article_number_extraction_template
)

article_choose_tool_prompt = PromptTemplate(
    input_variables=["article_number", "articles"],
    template=article_choose_prompt
)



