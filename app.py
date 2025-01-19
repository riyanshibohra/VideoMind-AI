import streamlit as st
import os
from src.utils import download_mp4_from_youtube
from src.transcriber import transcribe_video
from src.summarizer import summarize_text
from dotenv import load_dotenv
import pyperclip

# Load environment variables
load_dotenv()

# Initialize session state
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'show_copy_success' not in st.session_state:
    st.session_state.show_copy_success = False

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
        This tool helps you quickly understand YouTube videos by providing AI-powered summaries.
        
        ### Features
        - 🎥 Video transcription
        - 📝 Smart summarization
        - ⚡ Fast processing
        """)

    # Main content
    st.title("YouTube Video Summarizer")
    st.markdown("""
    Enter a YouTube video URL below to get started. The AI will transcribe the video 
    and generate a concise summary of its content.
    """)
    
    # URL input with validation
    youtube_url = st.text_input("Enter YouTube Video URL", 
                               placeholder="https://www.youtube.com/watch?v=...")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        process_button = st.button("🚀 Generate Summary", use_container_width=True)
    
    if youtube_url and process_button:
        try:
            # Create progress bar
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            # Download video
            status_text.info("📥 Downloading video...")
            progress_bar.progress(25)
            video_path = download_mp4_from_youtube(youtube_url)
            
            # Transcribe video
            status_text.info("🎯 Transcribing video...")
            progress_bar.progress(50)
            transcript = transcribe_video(video_path)
            
            # Generate summary
            status_text.info("🤖 Generating summary...")
            progress_bar.progress(75)
            summary = summarize_text(transcript)
            
            # Store in session state
            st.session_state.summary = summary
            st.session_state.transcript = transcript
            
            # Complete
            progress_bar.progress(100)
            status_text.success("✅ Processing complete!")
            
            # Clean up
            if os.path.exists(video_path):
                os.remove(video_path)
                
        except Exception as e:
            st.error("⚠️ An error occurred. Please check your URL and try again.")
            st.write(f"<span class='error-message'>Details: {str(e)}</span>", unsafe_allow_html=True)

    # Display results if available
    if st.session_state.summary and st.session_state.transcript:
        st.markdown("---")
        tabs = st.tabs(["📝 Summary", "🎯 Full Transcript"])
        
        with tabs[0]:
            st.markdown("### Video Summary")
            st.markdown(st.session_state.summary)
            col1, col2, col3 = st.columns([1, 8, 1])
            with col1:
                if st.button("📋 Copy", key="copy_summary"):
                    copy_to_clipboard(st.session_state.summary, "summary")
            with col2:
                if st.session_state.get('show_copy_success_summary', False):
                    st.success("✅ Summary copied to clipboard!")
                    st.session_state['show_copy_success_summary'] = False
                
        with tabs[1]:
            st.markdown("### Full Transcript")
            st.markdown(st.session_state.transcript)
            col1, col2, col3 = st.columns([1, 8, 1])
            with col1:
                if st.button("📋 Copy", key="copy_transcript"):
                    copy_to_clipboard(st.session_state.transcript, "transcript")
            with col2:
                if st.session_state.get('show_copy_success_transcript', False):
                    st.success("✅ Transcript copied to clipboard!")
                    st.session_state['show_copy_success_transcript'] = False

if __name__ == "__main__":
    main() 