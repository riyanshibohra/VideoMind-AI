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
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        background-color: #FF0000;
        color: white;
    }
    .stButton > button:hover {
        background-color: #CC0000;
        color: white;
    }
    .success-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D4EDDA;
        color: #155724;
        margin-top: 1rem;
    }
    .error-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #F8D7DA;
        color: #721C24;
    }
    .copy-btn {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        background-color: #FF0000;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 1rem;
        margin-top: 1rem;
        transition: background-color 0.3s ease;
    }
    .copy-btn:hover {
        background-color: #CC0000;
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
        
        ### Features:
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
    youtube_url = st.text_input("🔗 Enter YouTube Video URL:", 
                               placeholder="https://www.youtube.com/watch?v=...")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        process_button = st.button("🚀 Generate Summary")
    
    if youtube_url and process_button:
        try:
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Download video
            status_text.text("📥 Downloading video...")
            progress_bar.progress(25)
            video_path = download_mp4_from_youtube(youtube_url)
            
            # Transcribe video
            status_text.text("🎯 Transcribing video...")
            progress_bar.progress(50)
            transcript = transcribe_video(video_path)
            
            # Generate summary
            status_text.text("🤖 Generating summary...")
            progress_bar.progress(75)
            summary = summarize_text(transcript)
            
            # Store in session state
            st.session_state.summary = summary
            st.session_state.transcript = transcript
            
            # Complete
            progress_bar.progress(100)
            status_text.text("✅ Processing complete!")
            
            # Clean up
            if os.path.exists(video_path):
                os.remove(video_path)
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.write('<span class="error-message">Please check your URL and try again.</span>', 
                    unsafe_allow_html=True)

    # Display results if available
    if st.session_state.summary and st.session_state.transcript:
        tab1, tab2 = st.tabs(["📝 Summary", "🎯 Full Transcript"])
        
        with tab1:
            st.markdown("### Video Summary")
            st.markdown(st.session_state.summary)
            
            # Copy button for summary with visual feedback
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("📋 Copy Summary", key="copy_summary"):
                    copy_to_clipboard(st.session_state.summary, "summary")
            
            if st.session_state.get('show_copy_success_summary', False):
                st.success("✅ Summary copied to clipboard!")
                # Reset after 3 seconds
                import time
                time.sleep(1)
                st.session_state['show_copy_success_summary'] = False
                
        with tab2:
            st.markdown("### Full Transcript")
            st.markdown(st.session_state.transcript)
            
            # Copy button for transcript with visual feedback
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("📋 Copy Transcript", key="copy_transcript"):
                    copy_to_clipboard(st.session_state.transcript, "transcript")
            
            if st.session_state.get('show_copy_success_transcript', False):
                st.success("✅ Transcript copied to clipboard!")
                # Reset after 3 seconds
                import time
                time.sleep(1)
                st.session_state['show_copy_success_transcript'] = False

if __name__ == "__main__":
    main() 