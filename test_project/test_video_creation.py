#!/usr/bin/env python3
"""Test video creation with minimal setup"""

import sys
import logging
from pathlib import Path
import tempfile
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_image(output_path, width=1920, height=1080, color="blue"):
    """Create a test image using PIL"""
    try:
        from PIL import Image, ImageDraw
        
        # Create a simple colored image
        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)
        
        # Add some text
        draw.text((width//2-100, height//2), "Test Image", fill="white")
        
        img.save(output_path)
        logger.info(f"Created test image: {output_path}")
        return True
    except ImportError:
        logger.error("PIL not available, creating dummy image file")
        with open(output_path, 'w') as f:
            f.write("dummy image")
        return False

def create_test_audio(output_path, duration=5.0):
    """Create a test audio file"""
    try:
        import numpy as np
        from scipy.io import wavfile
        
        # Generate a simple sine wave
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration))
        frequency = 440  # A4 note
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # Convert to 16-bit integer
        audio_data = (audio_data * 32767).astype(np.int16)
        
        wavfile.write(output_path, sample_rate, audio_data)
        logger.info(f"Created test audio: {output_path}")
        return True
    except ImportError:
        logger.warning("scipy not available, creating silent audio with FFmpeg")
        # Create a silent audio file using FFmpeg
        import subprocess
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(duration),
                "-c:a", "pcm_s16le",
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Created silent audio: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create audio file: {e}")
            return False

def test_ffmpeg_basic():
    """Test basic FFmpeg functionality"""
    import subprocess
    
    try:
        # Test FFmpeg version
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("✅ FFmpeg is available")
        logger.info(f"Version: {result.stdout.splitlines()[0]}")
        return True
    except Exception as e:
        logger.error(f"❌ FFmpeg test failed: {e}")
        return False

def test_simple_video_creation():
    """Test creating a simple video with FFmpeg"""
    import subprocess
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        image_path = temp_path / "test_image.png"
        audio_path = temp_path / "test_audio.wav"
        video_path = temp_path / "test_video.mp4"
        
        logger.info("Creating test files...")
        create_test_image(image_path)
        create_test_audio(audio_path)
        
        # Simple FFmpeg command to create video
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            "-pix_fmt", "yuv420p",
            str(video_path)
        ]
        
        logger.info("Running FFmpeg command...")
        logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            if video_path.exists() and video_path.stat().st_size > 0:
                logger.info(f"✅ Video created successfully: {video_path}")
                logger.info(f"File size: {video_path.stat().st_size} bytes")
                return True
            else:
                logger.error("❌ Video file not created or empty")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ FFmpeg command timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg command failed: {e}")
            logger.error(f"stderr: {e.stderr}")
            return False

def main():
    """Run video creation tests"""
    logger.info("🧪 Testing video creation components...")
    
    # Test 1: FFmpeg availability
    logger.info("Test 1: FFmpeg availability")
    if not test_ffmpeg_basic():
        return False
    
    # Test 2: Simple video creation
    logger.info("Test 2: Simple video creation")
    if not test_simple_video_creation():
        return False
    
    logger.info("🎉 All video creation tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 