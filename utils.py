import yt_dlp
import warnings
warnings.filterwarnings("ignore")

def download_mp4_from_youtube(url):
    """Download a YouTube video as MP4."""
    filename = "temp_video.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': filename,
        'quiet': True,
        'nocheckcertificate': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
    
    return filename 