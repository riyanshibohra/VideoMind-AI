import streamlit as st
import os
from src.utils import (
    download_mp4_from_youtube, 
    create_vector_store, 
    cleanup_temp_files,
    process_video,
    delete_from_pinecone,
    cleanup_pinecone
)
from src.transcriber import transcribe_video
from src.summarizer import summarize_text
from src.chat import get_chatbot
from dotenv import load_dotenv
import pyperclip
import concurrent.futures
import uuid

def reset_session_state():
    """Reset all session state variables"""
    st.session_state.summaries = {}
    st.session_state.transcripts = {}
    st.session_state.messages = []
    st.session_state.chatbot = None
    if st.session_state.session_id:
        delete_from_pinecone(session_id=st.session_state.session_id)
    st.session_state.session_id = None
    st.session_state.processed_urls = set()
    st.session_state.show_input = True
    st.session_state.current_tab = "📝 Summaries"
    st.session_state.video_titles = {}

# Load environment variables
load_dotenv()

# Clean up Pinecone completely on every page load
cleanup_pinecone()

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
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "📝 Summaries"
if 'tab_key' not in st.session_state:
    st.session_state.tab_key = 0
if 'video_titles' not in st.session_state:
    st.session_state.video_titles = {}

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
        height: 600px;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        margin: 1rem 0;
        position: relative;
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .chat-input-container {
        position: sticky;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #0E1117;
        padding: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        z-index: 100;
    }
    
    .message-container {
        margin: 0.5rem 0;
    }
    
    /* Override Streamlit's default padding for chat messages */
    .stChatMessage {
        background-color: transparent !important;
        padding: 0.5rem !important;
    }
    
    .stChatMessage > div {
        padding: 0.5rem !important;
        border-radius: 0.5rem !important;
    }
    
    /* User message styling */
    .stChatMessage[data-testid="user-message"] > div {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Assistant message styling */
    .stChatMessage[data-testid="assistant-message"] > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    
    .video-title {
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 0.25rem;
    }
    
    .video-url {
        font-size: 0.9rem;
        color: #8b949e;
        word-break: break-all;
    }
    
    .video-card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
    
    .sidebar-video-card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 0.75rem;
        border-radius: 4px;
        margin-bottom: 0.5rem;
        position: relative;
    }
    
    .sidebar-video-title {
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 0.25rem;
        word-break: break-word;
    }
    
    .sidebar-video-url {
        font-size: 0.8rem;
        color: #8b949e;
        word-break: break-all;
    }
    
    /* Override Streamlit's default button styling for delete buttons */
    .stButton > button.delete-btn {
        background-color: transparent !important;
        color: #666 !important;
        border: none !important;
        padding: 0.25rem 0.5rem !important;
        font-size: 0.8rem !important;
        opacity: 0.7;
        transition: all 0.2s;
    }
    
    .stButton > button.delete-btn:hover {
        background-color: rgba(255, 59, 59, 0.1) !important;
        color: #ff3b3b !important;
        opacity: 1;
    }
    
    .add-video-section {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Sidebar styles */
    .sidebar-content {
        color: white !important;
    }
    
    .sidebar-title {
        color: white !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    
    .sidebar-about {
        color: white !important;
        padding: 1rem 0;
    }
    
    .sidebar-features {
        color: white !important;
        margin-top: 1rem;
    }
    
    .add-video-section {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
    }
    
    .add-video-section label {
        color: white !important;
        font-weight: 500;
    }
    
    .stTextInput input {
        color: black !important;
    }
    
    /* Remove the grey box above YouTube URL */
    .stTextInput > div:first-child {
        display: none;
    }
    
    /* Main chat container */
    .chat-container {
        display: flex;
        flex-direction: column;
        height: calc(100vh - 300px);
        background-color: rgba(17, 19, 23, 0.7);
        border-radius: 0.5rem;
        margin: 1rem 0;
        overflow: hidden;
    }
    
    /* Messages area */
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    /* Input area */
    .chat-input {
        position: sticky;
        bottom: 0;
        background-color: #0E1117;
        padding: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Message styling */
    .stChatMessage {
        background-color: transparent !important;
        padding: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    .stChatMessage > div {
        padding: 0.75rem !important;
        border-radius: 0.5rem !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    
    /* User message specific styling */
    .stChatMessage[data-testid="user-message"] > div {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Ensure chat input is visible and properly styled */
    .stChatInputContainer {
        padding: 0.5rem;
        background-color: transparent;
    }
    
    /* Hide default streamlit margins */
    .main > div {
        padding-top: 0.5rem !important;
    }
    
    .stMarkdown {
        margin-bottom: 0.5rem;
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
                    url, result = future.result()
                    if result and 'transcript' in result:
                        texts_dict[url] = result['transcript']
                        st.session_state.transcripts[url] = result['transcript']
                        summary = summarize_text(result['transcript'])
                        st.session_state.summaries[url] = summary
                        st.session_state.processed_urls.add(url)
                        st.session_state.video_titles[url] = result.get('title', 'Untitled Video')
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
            
            # Clear the progress indicators and rerun to show tabs
            progress_bar.empty()
            status_text.empty()
            st.rerun()
            
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
    """Show the video management interface in the sidebar"""
    st.markdown('<div style="color: white;">', unsafe_allow_html=True)
    
    # Display current videos with delete buttons
    if st.session_state.processed_urls:
        st.markdown('<h3 style="color: white;">📺 Current Videos</h3>', unsafe_allow_html=True)
        
        # Add reset button
        if st.button("🔄 Reset All", type="secondary", help="Remove all videos and reset"):
            reset_session_state()
            st.rerun()
        
        for url in st.session_state.processed_urls:
            title = st.session_state.video_titles.get(url, 'Untitled Video')
            
            # Create columns for video info and delete button
            col1, col2 = st.columns([0.85, 0.15])
            
            with col1:
                st.markdown(
                    f"""
                    <div style="background-color: rgba(255, 255, 255, 0.1); padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem;">
                        <div style="color: white; font-size: 0.9rem; font-weight: 500; margin-bottom: 0.25rem; word-break: break-word;">{title}</div>
                        <div style="color: #8b949e; font-size: 0.8rem; word-break: break-all;">{url}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col2:
                if st.button("🗑️", key=f"delete_{url}", help="Delete video", type="secondary"):
                    # Delete from Pinecone if we have a session
                    if st.session_state.session_id:
                        delete_from_pinecone(session_id=st.session_state.session_id, url=url)
                    
                    # Remove from session state
                    st.session_state.processed_urls.remove(url)
                    st.session_state.summaries.pop(url, None)
                    st.session_state.transcripts.pop(url, None)
                    st.session_state.video_titles.pop(url, None)
                    
                    # If no videos left, reset session
                    if not st.session_state.processed_urls:
                        reset_session_state()
                    else:
                        # Recreate vector store with remaining videos
                        texts_dict = {url: st.session_state.transcripts[url] for url in st.session_state.processed_urls}
                        vectorstore, session_id = create_vector_store(texts_dict)
                        st.session_state.session_id = session_id
                        st.session_state.chatbot = get_chatbot(session_id)
                    
                    st.rerun()
    else:
        st.markdown('<div style="color: white;">No videos added yet</div>', unsafe_allow_html=True)
    
    # Add new video section
    st.markdown('<h3 style="color: white; margin-bottom: 15px;">➕ Add New Video</h3>', unsafe_allow_html=True)
    
    # Initialize key in session state if not exists
    if 'new_video_url' not in st.session_state:
        st.session_state.new_video_url = ""
    
    new_url = st.text_input(
        "YouTube URL:",
        key="new_video_url", 
        placeholder="https://www.youtube.com/watch?v=..."
    )

    if new_url:
        if new_url not in st.session_state.processed_urls:
            if st.button("Add Video", type="primary", use_container_width=True):
                if process_videos([new_url]):
                    st.success("✅ Video added successfully!")
                    # Clear the input field
                    st.session_state.new_video_url = ""
                    st.rerun()
        else:
            st.markdown('<div style="color: #ffa07a;">This video is already added</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def display_chat():
    """Display chat interface with fixed input and scrollable messages"""
    st.markdown("### Chat about All Videos")
    st.markdown("Ask questions about any of the videos - the AI will combine information from all of them!")
    
    # Create chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Messages area (scrollable)
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input area (fixed at bottom)
    st.markdown('<div class="chat-input">', unsafe_allow_html=True)
    if prompt := st.chat_input("Ask a question about the videos...", key="chat_input"):
        # Show user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Prepare video information
        videos_info = {
            url: {
                'title': st.session_state.video_titles.get(url, 'Untitled Video'),
                'transcript': st.session_state.transcripts.get(url, ''),
                'summary': st.session_state.summaries.get(url, '')
            }
            for url in st.session_state.processed_urls
        }
        
        # Show "AI is thinking" message
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = st.session_state.chatbot(prompt, videos_info)
        
        # Add messages to session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to update the chat history
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown('<h1 class="sidebar-title">🎥 YouTube Summarizer</h1>', unsafe_allow_html=True)
        st.markdown("---")
        
        if st.session_state.summaries:
            show_video_management()
        else:
            st.markdown("""
            <div class="sidebar-about">
            <h2>About</h2>
            <p>This tool helps you quickly understand multiple YouTube videos by providing AI-powered summaries.</p>
            
            <div class="sidebar-features">
            <h3>Features</h3>
            <ul>
                <li>🎥 Multi-video support</li>
                <li>📝 Smart summarization</li>
                <li>⚡ Fast processing</li>
                <li>💬 Interactive chat</li>
            </ul>
            </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Main content
    if not st.session_state.summaries:
        # Show initial input interface only when no videos are processed
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
    
    else:
        # Show only the tabs interface when videos are processed
        tab_options = ["📝 Summaries", "💬 Chat", "🎯 Transcripts"]
        current_tab_index = tab_options.index(st.session_state.current_tab)
        
        selected_tab = st.radio(
            "",
            tab_options,
            horizontal=True,
            label_visibility="collapsed",
            index=current_tab_index
        )
        
        if selected_tab != st.session_state.current_tab:
            st.session_state.current_tab = selected_tab
            st.rerun()
        
        st.markdown("---")
        
        # Display content based on selected tab
        if st.session_state.current_tab == "📝 Summaries":
            st.markdown("### Video Summaries")
            for url, summary in st.session_state.summaries.items():
                title = st.session_state.video_titles.get(url, 'Untitled Video')
                with st.expander(f"Summary for: {title}"):
                    st.markdown(summary)
                    if st.button("📋 Copy", key=f"copy_summary_{url}"):
                        copy_to_clipboard(summary, f"summary_{url}")
                    if st.session_state.get(f'show_copy_success_summary_{url}', False):
                        st.success("✅ Summary copied to clipboard!")
                        st.session_state[f'show_copy_success_summary_{url}'] = False
        
        elif st.session_state.current_tab == "💬 Chat":
            display_chat()
        
        else:  # Transcripts tab
            st.markdown("### Full Transcripts")
            for url, transcript in st.session_state.transcripts.items():
                title = st.session_state.video_titles.get(url, 'Untitled Video')
                with st.expander(f"Transcript for: {title}"):
                    st.markdown(transcript)
                    if st.button("📋 Copy", key=f"copy_transcript_{url}"):
                        copy_to_clipboard(transcript, f"transcript_{url}")
                    if st.session_state.get(f'show_copy_success_transcript_{url}', False):
                        st.success("✅ Transcript copied to clipboard!")
                        st.session_state[f'show_copy_success_transcript_{url}'] = False

if __name__ == "__main__":
    main() 