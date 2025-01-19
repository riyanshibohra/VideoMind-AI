import streamlit as st
import os
from src.utils import download_mp4_from_youtube
from src.transcriber import transcribe_video
from src.summarizer import summarize_text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    st.title("YouTube Video Summarizer")
    
    # Input for YouTube URL
    youtube_url = st.text_input("Enter YouTube Video URL:")
    
    if youtube_url:
        with st.spinner("Processing video..."):
            try:
                # Download video
                st.info("Downloading video...")
                video_path = download_mp4_from_youtube(youtube_url)
                
                # Transcribe video
                st.info("Transcribing video...")
                transcript = transcribe_video(video_path)
                
                # Show transcript
                with st.expander("Show Transcript"):
                    st.text(transcript)
                
                # Summarize transcript
                st.info("Generating summary...")
                summary = summarize_text(transcript)
                
                # Show summary
                st.subheader("Summary")
                st.write(summary)
                
                # Clean up
                if os.path.exists(video_path):
                    os.remove(video_path)
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 