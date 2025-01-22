import yt_dlp
import warnings
from langchain_community.vectorstores import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone as PineconeClient
from pinecone import ServerlessSpec
import os
import hashlib
import json
from functools import lru_cache

warnings.filterwarnings("ignore")

# Cache directory for processed videos
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def initialize_pinecone():
    """Initialize Pinecone index if it doesn't exist"""
    try:
        pc = PineconeClient()
        
        # Check if index exists
        existing_indexes = [index.name for index in pc.list_indexes()]
        
        if "youtube-summarizer" not in existing_indexes:
            # Create index with appropriate settings
            pc.create_index(
                name="youtube-summarizer",
                dimension=1536,  # OpenAI embeddings dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",  # AWS us-east-1 environment
                    region="us-east-1"
                )
            )
            print("Created new Pinecone index: youtube-summarizer")
    except Exception as e:
        print(f"Error initializing Pinecone: {str(e)}")
        raise e

def _safe_delete_operation(operation_func):
    """Helper function to handle delete operations with consistent error handling"""
    try:
        operation_func()
    except Exception as e:
        # Ignore 404 errors when deleting
        if "404" not in str(e):
            print(f"Error deleting from Pinecone: {str(e)}")

def delete_from_pinecone(session_id=None, url=None, delete_index=False):
    """Delete vectors from Pinecone
    Args:
        session_id: If provided, delete entire namespace
        url: If provided, delete vectors for specific URL
        delete_index: If True, delete all vectors from the index
    """
    try:
        # Initialize Pinecone client
        pc = PineconeClient()
        
        # Ensure index exists
        initialize_pinecone()
        
        index = pc.Index("youtube-summarizer")
        
        if delete_index:
            _safe_delete_operation(
                lambda: index.delete(delete_all=True)
            )
        elif session_id:
            _safe_delete_operation(
                lambda: index.delete(delete_all=True, namespace=session_id)
            )
        elif url:
            _safe_delete_operation(
                lambda: index.delete(
                    filter={"source": url},
                    namespace=session_id
                )
            )
    except Exception as e:
        # Only print error if it's not a 404
        if "404" not in str(e):
            print(f"Error deleting from Pinecone: {str(e)}")

def cleanup_pinecone():
    """Clean up the entire Pinecone index"""
    delete_from_pinecone(delete_index=True)

def generate_session_id(urls):
    """Generate a unique session ID from list of URLs"""
    urls_str = "".join(sorted(urls))  # Sort to ensure same ID for same URLs regardless of order
    return hashlib.md5(urls_str.encode()).hexdigest()

def cleanup_temp_files(urls, session_id=None):
    """Clean up temporary video files and optionally Pinecone vectors"""
    # Clean up temp files
    for url in urls:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        filename = f"temp_video_{url_hash}.mp4"
        if os.path.exists(filename):
            os.remove(filename)
    
    # Clean up Pinecone vectors if session_id provided
    if session_id:
        delete_from_pinecone(session_id=session_id)

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
        'format': 'worst[ext=mp4]', 
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

def get_video_info(url):
    """Get video title and other info from YouTube URL"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Untitled Video'),
                'url': url
            }
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return {
                'title': 'Untitled Video',
                'url': url
            }

def process_video(url, transcribe_func):
    """Process a single video - download and transcribe"""
    try:
        # Check cache first
        cached_data = load_from_cache(url)
        if cached_data and 'transcript' in cached_data:
            # Get video info even for cached videos
            video_info = get_video_info(url)
            cached_data['title'] = video_info['title']
            return url, cached_data

        # Get video info
        video_info = get_video_info(url)
        
        # Download and transcribe
        video_path = download_mp4_from_youtube(url)
        transcript = transcribe_func(video_path)
        
        # Cache the result with title
        result = {
            'transcript': transcript,
            'title': video_info['title']
        }
        save_to_cache(url, result)
        
        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
            
        return url, result
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        return url, None

def create_vector_store(texts_dict):
    """Create vector store from multiple video transcripts
    Args:
        texts_dict: Dictionary mapping video URLs to their transcripts
    """
    # Ensure Pinecone index exists
    initialize_pinecone()
    
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
    # Ensure Pinecone index exists
    initialize_pinecone()
    
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
        k=10
    )
    
    # Combine relevant texts with source information
    contexts = []
    for doc in relevant_docs:
        source_url = doc.metadata.get('source', 'Unknown source')
        context = f"From video ({source_url}):\n{doc.page_content}"
        contexts.append(context)
    
    return "\n\n".join(contexts) 