from langchain_core.prompts import PromptTemplate


news_list_template = """You are an expert news collector. Given the following news articles:
{articles}  

User requested: "{query}"

INSTRUCTIONS:
1. If the query contains specific topics (sports, politics, business, technology, international, etc.):
   - PRIORITIZE articles matching that topic first
   - Look at both category labels AND headlines for matches
   - Show all matching articles, then fill remaining slots with general news
   - Example: For "sports news" → show all sports articles first, then other important news

2. If the query is general (latest news, today's news, top news):
   - Select the most relevant and recent news articles
   - Choose articles that cover a variety of topics
   - Balance different sections or categories

3. TOPIC MATCHING KEYWORDS:
   - Sports: cricket, football, soccer, tennis, basketball, match, tournament, team, player, score, game
   - Politics: government, election, party, minister, parliament, political, policy, BNP, leader, vote
   - Business: economy, finance, market, company, trade, investment, banking, stock, economic
   - Technology: tech, AI, software, computer, internet, digital, innovation, startup
   - International: world, global, foreign, international, country names, diplomatic

4. OUTPUT FORMAT:
IMPORTANT: Show EXACTLY {top_n} articles - no more, no less.

List format:
1. **Headline:** [Title]
   **Category:** [Category]
   **URL:** [URL]

2. **Headline:** [Title]
   **Category:** [Category]
   **URL:** [URL]

[Continue numbering up to {top_n}]

CRITICAL: Stop at article number {top_n}. Do not exceed this limit."""



article_choose_prompt = """
From the articles provided, choose the one user has asked for.

Users asked for: {user_input}

Articles: {articles}

Analyze the articles and find the one that best matches the user's request. If user wants sports news, choose the article related to sports. If user wants the 3rd article, choose the 3rd article. 

Answer: Return the chosen article's url chosen by the user only.

For example:

user: I want to know more about 4th news article. or I want to read the article about the sport article.

articles:
1. [Title of 1st article](url1)
2. [Title of 2nd article](url2)
3. [Title of 3rd article](url3)
4. [Title of 4th article](url4)

Answer: url4
Answer with only the url.

"""



news_explainer_template = """
You are an expert news explainer. Given the following news article:

{article}

Find the Key events or information and explain the news article. Include the following points:

1. Keep the main theme of the article.
2. Point out the key events/details mentioned in the article.
3. Summarize the article in a concise manner.
4. Use simple and clear language.
5. Keep the original meaning and context of the article.

DO NOT include any personal opinions or external information. Stick to the content provided in the article.

"""


news_list_prompt = PromptTemplate(
    input_variables=["articles", "top_n", "query"],
    template=news_list_template
)
article_choose_tool_prompt = PromptTemplate(
    input_variables=["user_input", "articles"],
    template=article_choose_prompt
)

news_explainer_prompt = PromptTemplate(
    input_variables=["article"],
    template=news_explainer_template
)



