import logging
from pathlib import Path
from src.bedtime_video_creator import BedtimeVideoCreator
import glob
import subprocess
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_intermediate_video(images, scene_durations, output_dir, batch_num):
    """Create a video for a batch of images"""
    # Create ffmpeg command
    cmd = ["ffmpeg", "-y"]  # Overwrite output file
    
    # Add inputs
    for img in images:
        cmd.extend([
            "-loop", "1",
            "-t", str(scene_durations[images.index(img)]),
            "-i", img["image_path"]
        ])
    
    # Create filter string
    filter_parts = []
    
    # Scale each image
    for i in range(len(images)):
        filter_parts.append(
            f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=disable,"
            f"setsar=1,fps=30[img{i}]"
        )
    
    # Add fades
    faded_inputs = []
    for i in range(len(images)):
        duration = scene_durations[i]
        fade_duration = min(0.5, duration / 4)
        filter_parts.append(
            f"[img{i}]fade=t=in:st=0:d={fade_duration},"
            f"fade=t=out:st={duration - fade_duration}:d={fade_duration}[faded{i}]"
        )
        faded_inputs.append(f"[faded{i}]")
    
    # Concatenate
    filter_parts.append(
        f"{''.join(faded_inputs)}concat=n={len(faded_inputs)}:v=1:a=0[v]"
    )
    
    # Add filter complex
    cmd.extend(["-filter_complex", ";".join(filter_parts)])
    
    # Output settings
    output_file = output_dir / f"intermediate_{batch_num}.mp4"
    cmd.extend([
        "-map", "[v]",
        "-c:v", "h264_videotoolbox",
        "-b:v", "2M",
        "-maxrate", "3M",
        "-bufsize", "6M",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        str(output_file)
    ])
    
    # Run command
    subprocess.run(cmd, check=True)
    return output_file

def combine_videos_with_audio(video_files, audio_file, output_dir, subtitle_file=None):
    """Combine intermediate videos with audio"""
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
    output_file = output_dir / f"final_video_{Path(audio_file).stem.split('_')[-1]}.mp4"
    
    if subtitle_file:
        # If we have subtitles, we need to re-encode
        cmd.extend([
            "-vf", f"subtitles={subtitle_file}:force_style='FontName=Arial,FontSize=24,"
            "PrimaryColour=&Hffffff,OutlineColour=&H40000000,BackColour=&H40000000,"
            "Outline=2,Shadow=1,MarginV=50'",
            "-c:v", "h264_videotoolbox",  # Use hardware encoding
            "-b:v", "2M",  # Maintain quality
            "-maxrate", "3M",
            "-bufsize", "6M"
        ])
    else:
        # Without subtitles we can just copy
        cmd.extend(["-c:v", "copy"])
    
    # Audio settings
    cmd.extend([
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-shortest",
        str(output_file)
    ])
    
    # Run command
    subprocess.run(cmd, check=True)
    
    # Clean up
    concat_file.unlink()
    for video in video_files:
        video.unlink()
    
    return output_file

def main():
    # Initialize paths
    output_dir = Path("OUTPUT/ancient_babylon")
    
    # Get all scene images
    images = []
    scene_durations = []
    
    # Get the audio file
    final_audio_path = output_dir / "final_audio_20250720_220949.wav"
    subtitle_path = output_dir / "subtitle_20250720_222224.srt"
    
    # Get all scene images and their durations
    for i in range(1, 201):  # Assuming 200 scenes
        scene_file = output_dir / f"scene_{i:03d}_20250720_220949.wav"
        if scene_file.exists():
            # Find corresponding image (any timestamp)
            image_pattern = str(output_dir / f"scene_{i:03d}_*.png")
            image_files = glob.glob(image_pattern)
            if image_files:  # Take the first matching image if multiple exist
                image_file = image_files[0]
                images.append({
                    "scene_number": i,
                    "image_path": image_file
                })
                
                # Get audio duration using ffprobe
                cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(scene_file)
                ]
                duration = float(subprocess.check_output(cmd).decode().strip())
                scene_durations.append(duration)
                logger.info(f"Added scene {i} with duration {duration:.2f}s")
    
    logger.info(f"Found {len(images)} images and audio files")
    
    # Process in batches of 20
    BATCH_SIZE = 20
    intermediate_videos = []
    
    for i in range(0, len(images), BATCH_SIZE):
        batch_images = images[i:i+BATCH_SIZE]
        batch_durations = scene_durations[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        logger.info(f"Processing batch {batch_num} ({len(batch_images)} images)")
        try:
            video_file = create_intermediate_video(
                batch_images,
                batch_durations,
                output_dir,
                batch_num
            )
            intermediate_videos.append(video_file)
            logger.info(f"Created intermediate video: {video_file}")
        except Exception as e:
            logger.error(f"Failed to create batch {batch_num}: {e}")
            return
    
    # Combine all videos with audio
    try:
        final_video = combine_videos_with_audio(
            intermediate_videos,
            final_audio_path,
            output_dir,
            subtitle_path
        )
        logger.info(f"Created final video: {final_video}")
    except Exception as e:
        logger.error(f"Failed to combine videos: {e}")
        return

if __name__ == "__main__":
    main() 