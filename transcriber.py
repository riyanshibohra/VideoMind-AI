import whisper

def transcribe_video(video_path):
    """Transcribe a video file using Whisper."""
    model = whisper.load_model("base")
    result = model.transcribe(video_path)
    return result["text"] 