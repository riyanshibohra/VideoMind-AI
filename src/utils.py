import yt_dlp
import warnings
from langchain_community.vectorstores import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone as PineconeClient
import os

warnings.filterwarnings("ignore")

def download_mp4_from_youtube(url):
    """Download a YouTube video as MP4."""
    filename = "temp_video.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': filename,
        'quiet': True,
        'nocheckcertificate': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
    
    return filename

def create_vector_store(text, video_url):
    """Create vector store from video transcript"""
    # Create text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    
    # Split text into chunks
    texts = text_splitter.split_text(text)
    
    # Create metadata for each chunk
    metadatas = [{"source": video_url, "chunk": i} for i in range(len(texts))]
    
    # Create embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create vector store directly using Langchain
    vectorstore = Pinecone.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        index_name="youtube-summarizer",
        namespace=video_url  # Use namespace instead of filter for separation
    )
    
    return vectorstore

def get_video_context(query, video_url):
    """Get relevant context from vector store for a query"""
    # Create embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create vector store
    vectorstore = Pinecone.from_existing_index(
        index_name="youtube-summarizer",
        embedding=embeddings,
        namespace=video_url  # Use the same namespace to get video-specific content
    )
    
    # Search for relevant context
    relevant_docs = vectorstore.similarity_search(
        query,
        k=3
    )
    
    # Combine relevant texts
    context = "\n\n".join([doc.page_content for doc in relevant_docs])
    
    return context 