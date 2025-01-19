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
    # Initialize Pinecone
    pc = PineconeClient(api_key=os.getenv('PINECONE_API_KEY'))
    
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
    
    # Initialize or get Pinecone index
    index_name = "youtube-summarizer"
    if index_name not in pc.list_indexes():
        pc.create_index(
            name=index_name,
            dimension=1536,  # OpenAI embeddings dimension
            metric="cosine"
        )
    
    # Get index
    index = pc.Index(index_name)
    
    # Create vector store
    vectorstore = Pinecone(
        index=index,
        embedding=embeddings,
        text_key="text"
    )
    
    # Add texts to vector store
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    
    return vectorstore

def get_video_context(query, video_url):
    """Get relevant context from vector store for a query"""
    # Initialize Pinecone and get index
    pc = PineconeClient(api_key=os.getenv('PINECONE_API_KEY'))
    index = pc.Index("youtube-summarizer")
    
    # Create embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create vector store
    vectorstore = Pinecone(
        index=index,
        embedding=embeddings,
        text_key="text"
    )
    
    # Search for relevant context
    relevant_docs = vectorstore.similarity_search(
        query,
        k=3,
        filter={"source": video_url}
    )
    
    # Combine relevant texts
    context = "\n\n".join([doc.page_content for doc in relevant_docs])
    
    return context 