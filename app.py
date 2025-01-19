import streamlit as st
import os
from src.utils import (
    download_mp4_from_youtube, 
    create_vector_store, 
    cleanup_temp_files,
    process_video
)
from src.transcriber import transcribe_video
from src.summarizer import summarize_text
from src.chat import get_chatbot
from dotenv import load_dotenv
import pyperclip
import concurrent.futures

# Load environment variables
load_dotenv()

# Initialize session state
if 'summaries' not in st.session_state:
    st.session_state.summaries = {}
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = {}
if 'show_copy_success' not in st.session_state:
    st.session_state.show_copy_success = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0
if 'processed_urls' not in st.session_state:
    st.session_state.processed_urls = set()
if 'show_input' not in st.session_state:
    st.session_state.show_input = True

# Page configuration
st.set_page_config(
    page_title="YouTube Video Summarizer",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 1.5rem;
    }
    .stButton > button {
        background-color: #FF0000;
        color: white;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #CC0000;
    }
    .success-message {
        padding: 0.75rem;
        border-radius: 6px;
        background-color: #28a745;
        color: white;
        margin: 0.5rem 0;
    }
    .error-message {
        padding: 0.75rem;
        border-radius: 6px;
        background-color: #dc3545;
        color: white;
        margin: 0.5rem 0;
    }
    h1 {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }
    .stProgress > div > div {
        background-color: #FF0000;
    }
    .stTextInput > div > div > input {
        background-color: #f8f9fa;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #f8f9fa;
        margin-left: 2rem;
    }
    .assistant-message {
        background-color: #f1f8ff;
        margin-right: 2rem;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 600px;
        gap: 1rem;
    }
    
    .chat-messages {
        flex-grow: 1;
        overflow-y: auto;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 0.5rem;
        background-color: rgba(255, 255, 255, 0.05);
    }
    
    .chat-input {
        position: sticky;
        bottom: 0;
        background-color: #0E1117;
        padding: 1rem 0;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    div[data-testid="stVerticalBlock"] > div:has(> div.chat-message) {
        overflow-y: auto;
        max-height: calc(100vh - 200px);
        padding-right: 1rem;
    }
    
    .video-list {
        margin: 1rem 0;
        padding: 1rem;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 0.5rem;
    }
    
    .video-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .video-item:last-child {
        border-bottom: none;
    }
    
    .manage-videos-btn {
        background-color: transparent;
        border: 1px solid #FF0000;
        color: #FF0000;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .manage-videos-btn:hover {
        background-color: #FF0000;
        color: white;
    }
    
    .chat-window {
        display: flex;
        flex-direction: column;
        height: calc(100vh - 300px);
        min-height: 400px;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .chat-messages {
        flex-grow: 1;
        overflow-y: auto;
        padding: 1rem;
        display: flex;
        flex-direction: column-reverse;
    }
    
    .chat-input-container {
        position: sticky;
        bottom: 0;
        background-color: #0E1117;
        padding: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        margin-top: auto;
    }
    
    .message-container {
        margin: 0.5rem 0;
    }
    
    /* Override Streamlit's default padding for chat messages */
    .stChatMessage {
        padding: 0.5rem !important;
        background-color: transparent !important;
    }
    </style>
""", unsafe_allow_html=True)

def copy_to_clipboard(text, key):
    """Helper function to copy text and show success message"""
    try:
        pyperclip.copy(text)
        st.session_state[f'show_copy_success_{key}'] = True
    except Exception as e:
        st.error(f"Failed to copy: {str(e)}")

def process_videos(urls):
    """Process multiple videos and update session state"""
    try:
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process videos in parallel
        status_text.info("🎥 Processing videos...")
        texts_dict = {}
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_url = {
                executor.submit(process_video, url, transcribe_video): url 
                for url in urls
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    url, transcript = future.result()
                    if transcript:
                        texts_dict[url] = transcript
                        summary = summarize_text(transcript)
                        st.session_state.transcripts[url] = transcript
                        st.session_state.summaries[url] = summary
                        st.session_state.processed_urls.add(url)
                except Exception as e:
                    st.error(f"Error processing {url}: {str(e)}")
                
                completed += 1
                progress = int((completed / len(urls)) * 90)
                progress_bar.progress(progress)
                status_text.info(f"✅ Processed {completed}/{len(urls)} videos...")
        
        if texts_dict:
            status_text.info("🧠 Creating vector store...")
            vectorstore, session_id = create_vector_store(texts_dict)
            st.session_state.session_id = session_id
            st.session_state.chatbot = get_chatbot(session_id)
            
            progress_bar.progress(100)
            status_text.success("✅ Processing complete!")
            st.session_state.show_input = False
            return True
        else:
            status_text.error("❌ No videos were successfully processed")
            return False
            
    except Exception as e:
        st.error("⚠️ An error occurred. Please check your URLs and try again.")
        st.write(f"<span class='error-message'>Details: {str(e)}</span>", unsafe_allow_html=True)
        cleanup_temp_files(urls)
        return False

def show_video_management():
    """Show the video management interface"""
    st.markdown("### 📺 Managed Videos")
    
    # Display current videos
    if st.session_state.processed_urls:
        for url in st.session_state.processed_urls:
            col1, col2 = st.columns([6, 1])
            with col1:
                st.write(url)
            with col2:
                if st.button("🗑️", key=f"delete_{url}"):
                    st.session_state.processed_urls.remove(url)
                    st.session_state.summaries.pop(url, None)
                    st.session_state.transcripts.pop(url, None)
                    st.rerun()
    
    # Add new videos
    new_url = st.text_input("Add new video URL:")
    if new_url and st.button("Add Video"):
        if new_url not in st.session_state.processed_urls:
            if process_videos([new_url]):
                st.success("✅ Video added successfully!")
                st.rerun()

def display_chat():
    """Display chat interface with fixed input and scrollable messages"""
    st.markdown("### Chat about All Videos")
    st.markdown("Ask questions about any of the videos - the AI will combine information from all of them!")
    
    # Create the main chat window
    chat_window = st.container()
    
    with chat_window:
        # Create a container for the entire chat interface
        st.markdown('<div class="chat-window">', unsafe_allow_html=True)
        
        # Messages container (displayed in reverse order)
        messages_container = st.container()
        
        # Input container at the bottom
        st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
        if prompt := st.chat_input("Ask a question about the videos...", key="chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            response = st.session_state.chatbot(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response})
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display messages in reverse chronological order
        with messages_container:
            st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
            for message in reversed(st.session_state.messages):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    # Sidebar
    with st.sidebar:
        st.markdown("# 🎥 YouTube Summarizer")
        st.markdown("---")
        st.markdown("""
        ## About
        This tool helps you quickly understand multiple YouTube videos by providing AI-powered summaries.
        
        ### Features
        - 🎥 Multi-video support
        - 📝 Smart summarization
        - ⚡ Fast processing
        - 💬 Interactive chat
        """)
        
        # Add video management button in sidebar
        if not st.session_state.show_input and st.button("📝 Manage Videos"):
            st.session_state.show_input = True
            st.rerun()

    # Main content
    if st.session_state.show_input:
        st.title("YouTube Video Summarizer")
        st.markdown("""
        Enter YouTube video URLs below (one per line) to get started. The AI will transcribe the videos, 
        generate summaries, and allow you to ask questions about all videos together.
        """)
        
        youtube_urls = st.text_area(
            "Enter YouTube Video URLs (one per line):", 
            height=100,
            placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=..."
        )
        
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            process_button = st.button("🚀 Process Videos", use_container_width=True)
        
        if youtube_urls and process_button:
            urls = [url.strip() for url in youtube_urls.split('\n') if url.strip()]
            process_videos(urls)
    
    # Display results if available
    if st.session_state.summaries:
        if st.session_state.show_input:
            st.markdown("---")
        
        # Show current videos
        st.markdown("### 🎥 Current Videos")
        for url in st.session_state.processed_urls:
            st.markdown(f"- {url}")
        
        # Create tabs without persistence
        tabs = st.tabs(["📝 Summaries", "💬 Chat", "🎯 Transcripts"])
        
        with tabs[0]:
            st.markdown("### Video Summaries")
            for url, summary in st.session_state.summaries.items():
                with st.expander(f"Summary for {url}"):
                    st.markdown(summary)
                    if st.button("📋 Copy", key=f"copy_summary_{url}"):
                        copy_to_clipboard(summary, f"summary_{url}")
                    if st.session_state.get(f'show_copy_success_summary_{url}', False):
                        st.success("✅ Summary copied to clipboard!")
                        st.session_state[f'show_copy_success_summary_{url}'] = False
        
        with tabs[1]:
            display_chat()
        
        with tabs[2]:
            st.markdown("### Full Transcripts")
            for url, transcript in st.session_state.transcripts.items():
                with st.expander(f"Transcript for {url}"):
                    st.markdown(transcript)
                    if st.button("📋 Copy", key=f"copy_transcript_{url}"):
                        copy_to_clipboard(transcript, f"transcript_{url}")
                    if st.session_state.get(f'show_copy_success_transcript_{url}', False):
                        st.success("✅ Transcript copied to clipboard!")
                        st.session_state[f'show_copy_success_transcript_{url}'] = False

if __name__ == "__main__":
    main() 