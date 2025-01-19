# YouTube Video Summarizer

A Python-based project that automatically generates concise summaries of YouTube videos using state-of-the-art AI technologies.

## Overview
This project combines OpenAI's Whisper for accurate speech-to-text transcription with LangChain's powerful language processing capabilities to create meaningful summaries of YouTube video content. 

By automating the summarization process, users can quickly grasp the key points of any YouTube video without watching the entire content.

## Key Features
- 🎥 Automatic YouTube video download and audio extraction
- 🗣️ High-quality speech-to-text transcription using Whisper
- 🤖 Intelligent summarization powered by LangChain
- ⚡ Support for various video lengths and content types
- 🎯 Easy-to-use web interface built with Streamlit

## Project Structure
```
youtube-video-summarizer/
├── src/                  # Source code
│   ├── app.py           # Main Streamlit application
│   ├── transcriber.py   # Handles video transcription using Whisper
│   ├── summarizer.py    # Manages text summarization with LangChain
│   └── utils.py         # Utility functions
├── data/                # Data directory
│   ├── temp/           # Temporary files
│   └── transcripts/    # Stored transcripts
├── tests/              # Test files
├── requirements.txt    # Project dependencies
├── README.md          # Project documentation
├── LICENSE            # MIT License
└── .env              # Environment variables (not tracked in git)
```

## Prerequisites
- Python 3.8 or higher
- OpenAI API key
- FFmpeg (for audio processing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/youtube-video-summarizer.git
cd youtube-video-summarizer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with the following:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the provided local URL (typically http://localhost:8501)

3. Enter a YouTube video URL and click "Generate Summary"

## How It Works
1. The system downloads the YouTube video and extracts its audio
2. Whisper processes the audio to generate accurate transcriptions
3. LangChain analyzes the transcription and creates a coherent summary
4. The summary is presented to the user in an easily digestible format

## Technologies Used
- Python
- OpenAI's Whisper - For accurate speech-to-text transcription
- LangChain - For advanced language processing and summarization
- Streamlit - For the web interface
- yt-dlp - For YouTube video downloading
- FFmpeg - For audio processing

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
- OpenAI for Whisper
- LangChain community
- Streamlit team
