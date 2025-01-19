from langchain_openai import OpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import os

def summarize_text(text):
    """Summarize text using LangChain and OpenAI."""
    # Initialize OpenAI LLM
    llm = OpenAI(
        model="gpt-3.5-turbo-instruct",
        temperature=0
    )

    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=0,
        separators=[" ", ",", "\n"]
    )

    # Convert text into documents
    texts = text_splitter.split_text(text)
    docs = [Document(page_content=t) for t in texts]

    # Create and run summarization chain
    chain = load_summarize_chain(llm, chain_type="map_reduce")
    summary = chain.run(docs)

    return summary 