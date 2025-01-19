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
    </style>
""", unsafe_allow_html=True)

def copy_to_clipboard(text, key):
    """Helper function to copy text and show success message"""
    try:
        pyperclip.copy(text)
        st.session_state[f'show_copy_success_{key}'] = True
    except Exception as e:
        st.error(f"Failed to copy: {str(e)}")

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

    # Main content
    st.title("YouTube Video Summarizer")
    st.markdown("""
    Enter YouTube video URLs below (one per line) to get started. The AI will transcribe the videos, 
    generate summaries, and allow you to ask questions about all videos together.
    """)
    
    # URL input with validation
    youtube_urls = st.text_area(
        "Enter YouTube Video URLs (one per line):", 
        height=100,
        placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=..."
    )
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        process_button = st.button("🚀 Process Videos", use_container_width=True)
    
    if youtube_urls and process_button:
        # Split URLs and clean them
        urls = [url.strip() for url in youtube_urls.split('\n') if url.strip()]
        
        try:
            # Create progress bar
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            # Process videos in parallel
            status_text.info("🎥 Processing videos...")
            texts_dict = {}
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit all video processing tasks
                future_to_url = {
                    executor.submit(process_video, url, transcribe_video): url 
                    for url in urls
                }
                
                # Process results as they complete
                completed = 0
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        url, transcript = future.result()
                        if transcript:  # Skip failed transcriptions
                            texts_dict[url] = transcript
                            
                            # Generate summary in parallel
                            summary = summarize_text(transcript)
                            st.session_state.transcripts[url] = transcript
                            st.session_state.summaries[url] = summary
                            
                    except Exception as e:
                        st.error(f"Error processing {url}: {str(e)}")
                    
                    # Update progress
                    completed += 1
                    progress = int((completed / len(urls)) * 90)  # Leave 10% for vector store creation
                    progress_bar.progress(progress)
                    status_text.info(f"✅ Processed {completed}/{len(urls)} videos...")
            
            if texts_dict:
                # Create vector store with all transcripts
                status_text.info("🧠 Creating vector store...")
                vectorstore, session_id = create_vector_store(texts_dict)
                
                # Store session info
                st.session_state.session_id = session_id
                st.session_state.chatbot = get_chatbot(session_id)
                st.session_state.messages = []
                
                # Complete
                progress_bar.progress(100)
                status_text.success("✅ Processing complete!")
            else:
                status_text.error("❌ No videos were successfully processed")
                
        except Exception as e:
            st.error("⚠️ An error occurred. Please check your URLs and try again.")
            st.write(f"<span class='error-message'>Details: {str(e)}</span>", unsafe_allow_html=True)
            cleanup_temp_files(urls)

    # Display results if available
    if st.session_state.summaries:
        st.markdown("---")
        tabs = st.tabs(["📝 Summaries", "🎯 Transcripts", "💬 Chat"])
        
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
            st.markdown("### Full Transcripts")
            for url, transcript in st.session_state.transcripts.items():
                with st.expander(f"Transcript for {url}"):
                    st.markdown(transcript)
                    if st.button("📋 Copy", key=f"copy_transcript_{url}"):
                        copy_to_clipboard(transcript, f"transcript_{url}")
                    if st.session_state.get(f'show_copy_success_transcript_{url}', False):
                        st.success("✅ Transcript copied to clipboard!")
                        st.session_state[f'show_copy_success_transcript_{url}'] = False
        
        with tabs[2]:
            st.markdown("### Chat about All Videos")
            st.markdown("Ask questions about any of the videos - the AI will combine information from all of them!")
            
            # Display chat messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Chat input
            if prompt := st.chat_input("Ask a question about the videos..."):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Get bot response
                with st.chat_message("assistant"):
                    response = st.session_state.chatbot(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main() 