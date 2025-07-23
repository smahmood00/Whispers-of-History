import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import platform

# Project root directory
ROOT_DIR = Path(__file__).parent.parent.absolute()

# Directory paths
OUTPUT_DIR = ROOT_DIR / "OUTPUT"
KOKORO_DIR = ROOT_DIR / "kokoro"
FFMPEG_DIR = ROOT_DIR / "ffmpeg"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# System configuration
IS_MACOS = platform.system() == "Darwin"


GEMINI_API_KEYS = [
    "AIzaSyCKS86JiBb0XTmTMGQVrNwwg7AOUTMfB8E",
    "AIzaSyBfDal9O-ugU1wrXF837EgiM7-zixyE2GM",
    "AIzaSyDfdkwYtNnpA6n2HffagHmN3jmTRPN8B4k",
    "AIzaSyDPn-HoAN8soPziVkS_3U09vNyWIj525Cg",
    "AIzaSyAlxoDPuwgP7xzBq4NcnQEcLU9ul85-9jY",
    "AIzaSyCSIhUamteuqDCZQO2Q8LgRYxLODCdH-0k",
    "AIzaSyAkXFrDx49svlapdb0BGz_jrtvWd6CjYvI",
    "AIzaSyAuhZ2wLE8LkaKEFnXA7EdPYU-4AlNH618",
    "AIzaSyCaLT4C6eFvGmiy8Cgn6wCLdOJekAJK2h0",
    "AIzaSyBlLw90kILHO3eFHI4mG-cnQWEui-S9CTE"
    # "AIzaSyCc69lZ8nKvjDrrfPaT0YTUKpWvBnJ0JEI",
    # "AIzaSyD7CqiLLS-dosUtUzMrLeB93z0Amv-P7c8",
    # "AIzaSyAMGdc-I8LnmHw1_xlA8p_VLnR6i1L1Wnc",
    # "AIzaSyDxTHu_civGr9nXxrToR2TPAo32htSWQTo",
    # "AIzaSyAtNO2DXfGnLn8ph8xNOdDKw92Pq4En6FI"
]



# Model Settings
STORY_MODEL = "gemini-1.5-flash"
IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"  # Updated to working model

# File Patterns
FILE_PATTERNS = {
    "story": "bedtime_story_{timestamp}.json",
    "scene_audio": "scene_{scene_number:03d}_{timestamp}.wav",
    "final_audio": "final_audio_{timestamp}.wav",
    "image": "scene_{scene_number:03d}_{timestamp}.png",
    "subtitle": "subtitle_{timestamp}.srt",
    "video": "bedtime_video_{timestamp}.mp4",
    "chapter_metadata": "chapter_{chapter_number:02d}_{timestamp}.json",
    "thumbnail": "thumbnail_{timestamp}.png",  # New pattern for thumbnails
    "pipeline_metadata": "pipeline_metadata_{timestamp}.json",
    "pipeline_metadata_error": "pipeline_metadata_error_{timestamp}.json"
}

# Whispers of History Channel Settings
BEDTIME_SETTINGS = {
    "target_word_count": 8000,  # Total word count for the story
    "scenes_per_chapter": 25,   # Each chapter has 25 scenes
    "voice": "am_onyx",
    "audio_speed": 0.75,
    "video_resolution": "1920x1080"
}

# Kokoro TTS Settings
KOKORO_SETTINGS = {
    "model_path": str(KOKORO_DIR / "kokoro-v1.0.onnx"),
    "voices_path": str(KOKORO_DIR / "voices-v1.0.bin"),
    "voice": "am_onyx",
    "speed": 0.85,
    "lang": "en-us"
}

# FFmpeg Settings
FFMPEG_SETTINGS = {
    "ffmpeg_path": str(FFMPEG_DIR / "ffmpeg.exe") if not IS_MACOS else "ffmpeg",
    "ffprobe_path": str(FFMPEG_DIR / "ffprobe.exe") if not IS_MACOS else "ffprobe"
} 

# YouTube Settings
YOUTUBE_SETTINGS = {
    "client_secrets_file": str(ROOT_DIR / "client_secrets.json"),
    "token_file": str(ROOT_DIR / "youtube_token.pickle"),
    "default_privacy": "public",  # Options: "private", "unlisted", "public"
    "default_category": "22",       # 22 = "People & Blogs", 27 = "Education"
    "notify_subscribers": False,
    "auto_upload": True,            # Whether to automatically upload videos
    "default_tags": [
        "bedtime history",
        "educational",
        "history for kids",
        "bedtime stories"
    ]
} 