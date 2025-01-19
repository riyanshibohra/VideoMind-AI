import yt_dlp
import warnings
from langchain_community.vectorstores import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone as PineconeClient
import os
import hashlib
import concurrent.futures
import json
from functools import lru_cache

warnings.filterwarnings("ignore")

# Cache directory for processed videos
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def generate_session_id(urls):
    """Generate a unique session ID from list of URLs"""
    urls_str = "".join(sorted(urls))  # Sort to ensure same ID for same URLs regardless of order
    return hashlib.md5(urls_str.encode()).hexdigest()

def cleanup_temp_files(urls):
    """Clean up temporary video files"""
    for url in urls:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        filename = f"temp_video_{url_hash}.mp4"
        if os.path.exists(filename):
            os.remove(filename)

def get_cache_path(url):
    """Get cache file path for a URL"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.json")

def save_to_cache(url, data):
    """Save processed data to cache"""
    cache_path = get_cache_path(url)
    with open(cache_path, 'w') as f:
        json.dump(data, f)

def load_from_cache(url):
    """Load processed data from cache"""
    cache_path = get_cache_path(url)
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)
    return None

def download_mp4_from_youtube(url):
    """Download a YouTube video as MP4."""
    # Check cache first
    cached_data = load_from_cache(url)
    if cached_data:
        return cached_data.get('filename')

    # Create unique filename based on URL
    url_hash = hashlib.md5(url.encode()).hexdigest()
    filename = f"temp_video_{url_hash}.mp4"
    
    ydl_opts = {
        'format': 'worst[ext=mp4]',  # Use lowest quality to speed up download
        'outtmpl': filename,
        'quiet': True,
        'nocheckcertificate': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
    
    # Cache the result
    save_to_cache(url, {'filename': filename})
    return filename

@lru_cache(maxsize=100)
def get_embeddings():
    """Cached embeddings instance"""
    return OpenAIEmbeddings()

def process_video(url, transcribe_func):
    """Process a single video - download and transcribe"""
    try:
        # Check cache first
        cached_data = load_from_cache(url)
        if cached_data and 'transcript' in cached_data:
            return url, cached_data['transcript']

        # Download and transcribe
        video_path = download_mp4_from_youtube(url)
        transcript = transcribe_func(video_path)
        
        # Cache the result
        save_to_cache(url, {'transcript': transcript})
        
        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
            
        return url, transcript
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        return url, None

def create_vector_store(texts_dict):
    """Create vector store from multiple video transcripts
    Args:
        texts_dict: Dictionary mapping video URLs to their transcripts
    """
    # Create text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    
    # Process all texts
    all_texts = []
    all_metadatas = []
    
    # Batch process texts
    for url, text in texts_dict.items():
        if text:  # Skip failed transcripts
            chunks = text_splitter.split_text(text)
            all_texts.extend(chunks)
            metadatas = [{"source": url, "chunk": i} for i in range(len(chunks))]
            all_metadatas.extend(metadatas)
    
    # Get cached embeddings
    embeddings = get_embeddings()
    
    # Generate session ID from all URLs
    session_id = generate_session_id(list(texts_dict.keys()))
    
    # Create vector store with batched operations
    vectorstore = Pinecone.from_texts(
        texts=all_texts,
        embedding=embeddings,
        metadatas=all_metadatas,
        index_name="youtube-summarizer",
        namespace=session_id,
        batch_size=100  # Process in larger batches
    )
    
    return vectorstore, session_id

def get_video_context(query, session_id):
    """Get relevant context from vector store for a query"""
    # Use cached embeddings
    embeddings = get_embeddings()
    
    # Create vector store
    vectorstore = Pinecone.from_existing_index(
        index_name="youtube-summarizer",
        embedding=embeddings,
        namespace=session_id
    )
    
    # Search for relevant context
    relevant_docs = vectorstore.similarity_search(
        query,
        k=5
    )
    
    # Combine relevant texts with source information
    contexts = []
    for doc in relevant_docs:
        source_url = doc.metadata.get('source', 'Unknown source')
        context = f"From video ({source_url}):\n{doc.page_content}"
        contexts.append(context)
    
    return "\n\n".join(contexts) 