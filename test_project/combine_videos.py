import logging
from pathlib import Path
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def combine_videos():
    output_dir = Path("OUTPUT/ancient_babylon")
    
    # Get intermediate videos in order
    video_files = []
    for i in range(1, 11):  # 10 batches
        video_file = output_dir / f"intermediate_{i}.mp4"
        if video_file.exists():
            video_files.append(video_file)
    
    logger.info(f"Found {len(video_files)} intermediate videos")
    
    # Get audio and subtitle files
    audio_file = output_dir / "final_audio_20250720_220949.wav"
    subtitle_file = output_dir / "subtitle_20250720_222224.srt"
    
    # Create concat file
    concat_file = output_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for video in video_files:
            f.write(f"file '{video.absolute()}'\n")
    
    # Create ffmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-i", str(audio_file)
    ]
    
    # Output settings
    output_file = output_dir / "final_video_220949.mp4"
    
    # Add subtitle filter and encoding settings
    cmd.extend([
        "-vf", f"subtitles={subtitle_file}:force_style='FontName=Arial,FontSize=24,"
        "PrimaryColour=&Hffffff,OutlineColour=&H40000000,BackColour=&H40000000,"
        "Outline=2,Shadow=1,MarginV=50'",
        "-c:v", "h264_videotoolbox",  # Use hardware encoding
        "-b:v", "2M",  # Maintain quality
        "-maxrate", "3M",
        "-bufsize", "6M",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-shortest",
        str(output_file)
    ])
    
    # Run command
    logger.info("Combining videos with audio and subtitles...")
    subprocess.run(cmd, check=True)
    
    # Clean up
    concat_file.unlink()
    
    logger.info(f"Created final video: {output_file}")

if __name__ == "__main__":
    combine_videos() 