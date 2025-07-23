import logging
from pathlib import Path
import glob
import subprocess
from src.bedtime_video_creator import BedtimeVideoCreator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    # Create video using improved BedtimeVideoCreator
    video_creator = BedtimeVideoCreator(output_dir=output_dir, batch_size=20)
    result = video_creator.process_bedtime_video(
        images=images,
        scene_durations=scene_durations,
        final_audio_path=final_audio_path,
        subtitle_path=subtitle_path
    )
    
    if result:
        logger.info(f"Video created successfully: {result['video_file']}")
        logger.info(f"Video duration: {result['metadata']['duration']:.2f}s")
        logger.info(f"Total audio duration: {result['metadata']['total_audio_duration']:.2f}s")
        
        # Verify durations match
        video_duration = result['metadata']['duration']
        audio_duration = result['metadata']['total_audio_duration']
        if abs(video_duration - audio_duration) > 1.0:  # Allow 1 second tolerance
            logger.warning(f"Video duration ({video_duration:.2f}s) doesn't match audio duration ({audio_duration:.2f}s)")
        else:
            logger.info("✅ Video and audio durations match!")
    else:
        logger.error("Failed to create video")

if __name__ == "__main__":
    main() 