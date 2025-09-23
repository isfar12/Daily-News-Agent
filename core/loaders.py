from langchain_community.document_loaders import TextLoader
import os
import pathlib

def load_news_articles():
    
    folder_path = os.path.join(pathlib.Path(__file__).parent.parent, "news")
    file_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.txt')]

    data = []
    for file_path in file_paths:
        text_loader = TextLoader(file_path, encoding='utf-8')
        data.extend(text_loader.load())
    return data
