from typing import List, Optional, Dict, Any, Union,Annotated
from pydantic import BaseModel, Field
from langchain.tools import tool

class NewsSummary(BaseModel):
    title: Annotated[str, Field(description="The title of the article")]
    content: Annotated[Optional[str], Field(description="The explained news article content")]
    url: Annotated[str, Field(description="The URL of the article for reference")]

class UrlOnly(BaseModel):
    url: Annotated[str, Field(description="The URL of the article")]
    