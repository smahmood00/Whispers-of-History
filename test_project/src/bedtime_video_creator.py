import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .config import (
    FILE_PATTERNS,
    FFMPEG_SETTINGS,
    BEDTIME_SETTINGS,
    IS_MACOS
)
from .base import BaseComponent

logger = logging.getLogger(__name__)

class BedtimeVideoCreator(BaseComponent):
    """Creates bedtime videos using FFmpeg with precise audio-image synchronization"""
    
    def __init__(self, output_dir: Optional[Path] = None, batch_size: int = 20):
        super().__init__(output_dir)
        self._verify_ffmpeg()
        self.batch_size = batch_size
    
    def _verify_ffmpeg(self) -> None:
        """Verify FFmpeg is available and log version info"""
        try:
            ffmpeg_cmd = FFMPEG_SETTINGS["ffmpeg_path"]
            result = subprocess.run(
                [ffmpeg_cmd, "-version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"FFmpeg version: {result.stdout.splitlines()[0]}")
            
            # Check for VideoToolbox support on macOS
            if IS_MACOS and "enable-videotoolbox" in result.stdout:
                logger.info("VideoToolbox hardware acceleration available")
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg check failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError(f"FFmpeg not found at: {FFMPEG_SETTINGS['ffmpeg_path']}")
    
    def _prepare_image_inputs(self, images: List[Dict[str, Any]], scene_durations: List[float]) -> List[str]:
        """Prepare FFmpeg input arguments for images with durations
        
        Args:
            images: List of image metadata with paths
            scene_durations: List of durations for each scene
            
        Returns:
            List of FFmpeg input arguments
        """
        inputs = []
        
        for i, (image, duration) in enumerate(zip(images, scene_durations)):
            image_path = image["image_path"]
            
            # Add image input with loop and duration
            inputs.extend([
                "-loop", "1",
                "-t", str(duration),
                "-i", image_path
            ])
        
        return inputs
    
    def _create_video_filter(self, images: List[Dict[str, Any]], scene_durations: List[float], subtitle_path: Optional[Path] = None) -> str:
        """Create FFmpeg filter for video assembly with transitions and subtitles
        
        Args:
            images: List of image metadata
            scene_durations: List of durations for each scene
            subtitle_path: Optional path to subtitle file
            
        Returns:
            FFmpeg filter string
        """
        filter_parts = []
        
        # Scale and prepare each image - force exact dimensions to avoid encoder issues
        for i in range(len(images)):
            filter_parts.append(
                f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=disable,"
                f"setsar=1,fps=30[img{i}]"
            )
        
        # Add fade transitions for smoother bedtime viewing
        faded_inputs = []
        for i in range(len(images)):
            duration = scene_durations[i]
            fade_duration = min(0.5, duration / 4)  # Fade duration is 1/4 of scene or 0.5s max
            
            filter_parts.append(
                f"[img{i}]fade=t=in:st=0:d={fade_duration},"
                f"fade=t=out:st={duration - fade_duration}:d={fade_duration}[faded{i}]"
            )
            faded_inputs.append(f"[faded{i}]")
        
        # Concatenate all video streams
        if len(faded_inputs) > 1:
            filter_parts.append(
                f"{''.join(faded_inputs)}concat=n={len(faded_inputs)}:v=1:a=0[concat_video]"
            )
        else:
            filter_parts.append(f"[faded0]copy[concat_video]")
        
        # Add subtitles if provided
        if subtitle_path and subtitle_path.exists():
            filter_parts.append(
                f"[concat_video]subtitles={subtitle_path}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H40000000,BackColour=&H40000000,Outline=2,Shadow=1,MarginV=50'[video]"
            )
        else:
            filter_parts.append(f"[concat_video]copy[video]")
        
        return ";".join(filter_parts)
    
    def _create_intermediate_video(self, 
                                  images: List[Dict[str, Any]], 
                                  scene_durations: List[float],
                                  batch_num: int) -> Path:
        """Create an intermediate video for a batch of images
        
        Args:
            images: List of image metadata with paths
            scene_durations: List of durations for each scene
            batch_num: Batch number for output filename
            
        Returns:
            Path to generated intermediate video file
        """
        logger.info(f"Creating intermediate video for batch {batch_num} ({len(images)} images)...")
        
        # Create output filename
        output_filename = f"intermediate_{batch_num}.mp4"
        output_path = self.output_dir / output_filename
        
        # Prepare FFmpeg command
        cmd = [FFMPEG_SETTINGS["ffmpeg_path"], "-y"]  # Overwrite output file
        
        # Add image inputs with durations
        image_inputs = self._prepare_image_inputs(images, scene_durations)
        cmd.extend(image_inputs)
        
        # Create video filter
        video_filter = self._create_video_filter(images, scene_durations)
        cmd.extend(["-filter_complex", video_filter])
        
        # Map video output
        cmd.extend(["-map", "[video]"])
        
        # Video encoding settings
        if IS_MACOS:
            # Use VideoToolbox on macOS for hardware acceleration
            cmd.extend([
                "-c:v", "h264_videotoolbox",
                "-b:v", "2M",  # 2 Mbps bitrate for good quality
                "-maxrate", "3M",
                "-bufsize", "6M"
            ])
        else:
            # Use software encoding
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23"
            ])
        
        # Output settings
        cmd.extend([
            "-pix_fmt", "yuv420p",
            "-r", "30",  # 30 fps
            "-movflags", "+faststart",  # Optimize for streaming
            str(output_path)
        ])
        
        # Run FFmpeg
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            logger.info(f"Intermediate video created successfully: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to create intermediate video: {e.stderr}")
    
    def _combine_videos(self, 
                       video_files: List[Path], 
                       final_audio_path: Path, 
                       subtitle_path: Optional[Path] = None) -> Path:
        """Combine intermediate videos with audio and subtitles
        
        Args:
            video_files: List of intermediate video files
            final_audio_path: Path to final audio file
            subtitle_path: Optional path to subtitle file
            
        Returns:
            Path to final video file
        """
        logger.info(f"Combining {len(video_files)} intermediate videos with audio...")
        
        # Create output filename
        timestamp = self.get_timestamp()
        output_filename = FILE_PATTERNS["video"].format(timestamp=timestamp)
        output_path = self.output_dir / output_filename
        
        # Create concat file for FFmpeg
        concat_file = self.output_dir / f"concat_{timestamp}.txt"
        with open(concat_file, "w") as f:
            for video in video_files:
                f.write(f"file '{video.absolute()}'\n")
        
        # Prepare FFmpeg command
        cmd = [
            FFMPEG_SETTINGS["ffmpeg_path"], "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-i", str(final_audio_path)
        ]
        
        # Handle subtitles - must re-encode if adding subtitles
        if subtitle_path and subtitle_path.exists():
            cmd.extend([
                "-vf", f"subtitles={subtitle_path}:force_style='FontName=Arial,FontSize=24,"
                "PrimaryColour=&Hffffff,OutlineColour=&H40000000,BackColour=&H40000000,"
                "Outline=2,Shadow=1,MarginV=50'",
                "-c:v", "h264_videotoolbox" if IS_MACOS else "libx264",
                "-b:v", "2M",
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
            "-shortest",  # End when shortest input ends
            str(output_path)
        ])
        
        # Run FFmpeg
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            logger.info(f"Final video created successfully: {output_path}")
            
            # Clean up
            concat_file.unlink()
            
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to combine videos: {e.stderr}")
    
    def _create_bedtime_video(self, 
                            images: List[Dict[str, Any]], 
                            scene_durations: List[float],
                            final_audio_path: Path, 
                            subtitle_path: Optional[Path] = None) -> Path:
        """Create bedtime video with precise timing and subtitles
        
        Args:
            images: List of image metadata with paths
            scene_durations: List of durations for each scene
            final_audio_path: Path to final combined audio
            subtitle_path: Optional path to subtitle file
            
        Returns:
            Path to generated video file
        """
        logger.info(f"Creating bedtime video with {len(images)} images...")
        
        # Process in batches to avoid memory issues
        intermediate_videos = []
        
        for i in range(0, len(images), self.batch_size):
            batch_images = images[i:i+self.batch_size]
            batch_durations = scene_durations[i:i+self.batch_size]
            batch_num = i // self.batch_size + 1
            
            try:
                video_file = self._create_intermediate_video(
                    batch_images,
                    batch_durations,
                    batch_num
                )
                intermediate_videos.append(video_file)
            except Exception as e:
                logger.error(f"Failed to create batch {batch_num}: {e}")
                # Clean up any created intermediates
                for video in intermediate_videos:
                    if video.exists():
                        video.unlink()
                raise
        
        # Combine all videos with audio
        try:
            final_video = self._combine_videos(
                intermediate_videos,
                final_audio_path,
                subtitle_path
            )
            
            # Clean up intermediate videos
            for video in intermediate_videos:
                if video.exists():
                    video.unlink()
            
            return final_video
        except Exception as e:
            logger.error(f"Failed to combine videos: {e}")
            # Clean up any created intermediates
            for video in intermediate_videos:
                if video.exists():
                    video.unlink()
            raise
    
    def _get_video_duration(self, video_path: Path) -> float:
        """Get duration of a video file in seconds
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        cmd = [
            FFMPEG_SETTINGS["ffprobe_path"],
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        return float(result.stdout.strip())
    
    def process_bedtime_video(self, 
                            images: List[Dict[str, Any]], 
                            scene_durations: List[float],
                            final_audio_path: Path, 
                            subtitle_path: Optional[Path] = None,
                            **kwargs) -> Dict[str, Any]:
        """Process all components into a bedtime video
        
        Args:
            images: List of image metadata with paths
            scene_durations: List of durations for each scene
            final_audio_path: Path to final combined audio
            subtitle_path: Optional path to subtitle file
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with video file path and metadata
        """
        logger.info(f"Processing bedtime video with {len(images)} images...")
        
        # Verify inputs
        if len(images) != len(scene_durations):
            raise ValueError("Number of images must match number of scene durations")
        
        for image in images:
            image_path = Path(image["image_path"])
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if not final_audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {final_audio_path}")
        
        if subtitle_path and not subtitle_path.exists():
            logger.warning(f"Subtitle file not found: {subtitle_path}")
            subtitle_path = None
        
        # Create video
        video_path = self._create_bedtime_video(
            images, 
            scene_durations, 
            final_audio_path, 
            subtitle_path
        )
        
        # Get video duration
        video_duration = self._get_video_duration(video_path)
        
        # Create metadata
        metadata = {
            "timestamp": self.get_timestamp(),
            "video_file": str(video_path),
            "duration": video_duration,
            "scene_count": len(images),
            "total_audio_duration": sum(scene_durations),
            "has_subtitles": subtitle_path is not None,
            "bedtime_optimized": True,
            "video_settings": {
                "resolution": "1920x1080",
                "fps": 30,
                "codec": "h264_videotoolbox" if IS_MACOS else "libx264",
                "audio_codec": "aac"
            },
            "scene_durations": scene_durations
        }
        
        logger.info(f"Bedtime video processing complete!")
        logger.info(f"Video duration: {video_duration:.2f}s")
        logger.info(f"Video file: {video_path}")
        
        return {
            "video_file": str(video_path),
            "metadata": metadata
        }
    
    def test(self) -> bool:
        """Test the bedtime video creator"""
        logger.info("[BedtimeVideoCreator] Running tests...")
        
        try:
            # Look for existing files to test with
            image_files = list(self.output_dir.glob("scene_*.png"))
            audio_files = list(self.output_dir.glob("final_audio_*.wav"))
            subtitle_files = list(self.output_dir.glob("subtitle_*.srt"))
            
            if not image_files or not audio_files:
                logger.warning("No test files found, skipping video creation test")
                return True
            
            # Use available files for testing
            test_images = [
                {
                    "scene_number": 1,
                    "image_path": str(image_files[0])
                }
            ]
            
            if len(image_files) > 1:
                test_images.append({
                    "scene_number": 2,
                    "image_path": str(image_files[1])
                })
            
            test_durations = [3.0] * len(test_images)  # 3 seconds per image
            test_audio = max(audio_files, key=lambda p: p.stat().st_mtime)
            test_subtitle = max(subtitle_files, key=lambda p: p.stat().st_mtime) if subtitle_files else None
            
            logger.info(f"Testing with {len(test_images)} images and audio: {test_audio.name}")
            
            # Create test video
            result = self.process_bedtime_video(
                test_images,
                test_durations,
                test_audio,
                test_subtitle
            )
            
            # Verify result
            video_path = Path(result["video_file"])
            if not video_path.exists():
                raise ValueError(f"Video file not created: {video_path}")
            
            # Check file size (should be > 0)
            if video_path.stat().st_size == 0:
                raise ValueError("Video file is empty")
            
            logger.info(f"[BedtimeVideoCreator] Test passed - created video: {video_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"[BedtimeVideoCreator] Test failed: {str(e)}")
            return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the creator
    creator = BedtimeVideoCreator()
    
    if creator.test():
        print("✅ BedtimeVideoCreator test passed!")
    else:
        print("❌ BedtimeVideoCreator test failed!") 