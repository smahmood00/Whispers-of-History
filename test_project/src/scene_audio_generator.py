import logging
import time
import soundfile as sf
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess
import os

from kokoro_onnx import Kokoro

from .config import (
    FILE_PATTERNS,
    KOKORO_SETTINGS,
    BEDTIME_SETTINGS
)
from .base import BaseComponent
from .utils import retry_with_backoff

logger = logging.getLogger(__name__)

class SceneAudioGenerator(BaseComponent):
    """Generates audio for individual scenes using Kokoro TTS"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self._setup_tts()
        
    def _setup_tts(self) -> None:
        """Initialize Kokoro TTS with proper settings"""
        try:
            # Check if model files exist
            model_path = Path(KOKORO_SETTINGS["model_path"])
            voices_path = Path(KOKORO_SETTINGS["voices_path"])
            
            if not model_path.exists():
                raise FileNotFoundError(f"Kokoro model not found at: {model_path}")
            if not voices_path.exists():
                raise FileNotFoundError(f"Kokoro voices not found at: {voices_path}")
            
            # Initialize TTS
            self.tts = Kokoro(
                model_path=str(model_path),
                voices_path=str(voices_path)
            )
            
            logger.info("Successfully initialized Kokoro TTS")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro TTS: {str(e)}")
            raise RuntimeError(f"TTS initialization failed: {str(e)}")
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean and prepare text for TTS processing
        
        Args:
            text: Raw narration text
            
        Returns:
            Cleaned text ready for TTS
        """
        # Remove any special characters that might cause issues
        cleaned = text.replace('"', '"').replace('"', '"')
        cleaned = cleaned.replace(''', "'").replace(''', "'")
        cleaned = cleaned.replace('…', '...')
        
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Ensure text ends with proper punctuation for natural speech
        if not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
        
        return cleaned
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _generate_scene_audio(self, scene_text: str, scene_number: int, timestamp: str) -> Dict[str, Any]:
        """Generate audio for a single scene
        
        Args:
            scene_text: Scene narration text
            scene_number: Scene number for filename
            timestamp: Timestamp for filename
            
        Returns:
            Dictionary with audio file path and metadata
        """
        try:
            start_time = time.time()
            
            # Clean text for TTS
            cleaned_text = self._clean_text_for_tts(scene_text)
            
            logger.info(f"Generating audio for scene {scene_number}...")
            
            # Generate audio using Kokoro TTS
            samples, sample_rate = self.tts.create(
                cleaned_text,
                voice=KOKORO_SETTINGS["voice"],
                speed=KOKORO_SETTINGS["speed"],
                lang=KOKORO_SETTINGS["lang"]
            )
            
            # Create filename
            audio_filename = FILE_PATTERNS["scene_audio"].format(
                scene_number=scene_number,
                timestamp=timestamp
            )
            audio_path = self.output_dir / audio_filename
            
            # Save audio file
            sf.write(str(audio_path), samples, sample_rate)
            
            # Calculate duration and processing time
            duration = len(samples) / sample_rate
            processing_time = time.time() - start_time
            
            logger.info(f"Scene {scene_number} audio generated in {processing_time:.2f}s (duration: {duration:.2f}s)")
            
            return {
                "scene_number": scene_number,
                "audio_file": str(audio_path),
                "duration": duration,
                "sample_rate": sample_rate,
                "processing_time": processing_time,
                "word_count": len(cleaned_text.split()),
                "cleaned_text": cleaned_text
            }
            
        except Exception as e:
            logger.error(f"Error generating audio for scene {scene_number}: {str(e)}")
            raise
    
    def _combine_audio_files(self, scene_audios: List[Dict[str, Any]], timestamp: str) -> Dict[str, Any]:
        """Combine all scene audio files into one final audio file
        
        Args:
            scene_audios: List of scene audio metadata
            timestamp: Timestamp for filename
            
        Returns:
            Dictionary with combined audio file path and metadata
        """
        try:
            logger.info("Combining scene audio files...")
            
            # Create final audio filename
            final_audio_filename = FILE_PATTERNS["final_audio"].format(timestamp=timestamp)
            final_audio_path = self.output_dir / final_audio_filename
            
            # Use ffmpeg to concatenate audio files
            audio_files = [scene["audio_file"] for scene in scene_audios]
            
            # Create a temporary file list for ffmpeg
            concat_file = self.output_dir / f"concat_list_{timestamp}.txt"
            with open(concat_file, 'w') as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file}'\n")
            
            # Run ffmpeg to concatenate
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(final_audio_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Clean up temporary file
            concat_file.unlink()
            
            # Calculate total duration
            total_duration = sum(scene["duration"] for scene in scene_audios)
            
            logger.info(f"Combined audio saved to: {final_audio_path}")
            logger.info(f"Total duration: {total_duration:.2f}s")
            
            return {
                "final_audio_file": str(final_audio_path),
                "total_duration": total_duration,
                "scene_count": len(scene_audios),
                "individual_durations": [scene["duration"] for scene in scene_audios]
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError("Failed to combine audio files")
        except Exception as e:
            logger.error(f"Error combining audio files: {str(e)}")
            raise
    
    def process_scenes(self, scenes: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Process all scenes to generate individual and combined audio
        
        Args:
            scenes: List of scene data with narration_text
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with scene audio data and combined audio
        """
        logger.info(f"Processing {len(scenes)} scenes for audio generation...")
        
        timestamp = self.get_timestamp()
        scene_audios = []
        
        # Generate audio for each scene
        for scene in scenes:
            scene_audio = self._generate_scene_audio(
                scene["narration_text"],
                scene["scene_number"],
                timestamp
            )
            scene_audios.append(scene_audio)
        
        # Combine all audio files
        combined_audio = self._combine_audio_files(scene_audios, timestamp)
        
        # Create comprehensive metadata
        metadata = {
            "timestamp": timestamp,
            "scene_count": len(scenes),
            "total_words": sum(audio["word_count"] for audio in scene_audios),
            "total_duration": combined_audio["total_duration"],
            "avg_duration_per_scene": combined_audio["total_duration"] / len(scenes),
            "voice_settings": {
                "voice": KOKORO_SETTINGS["voice"],
                "speed": KOKORO_SETTINGS["speed"],
                "lang": KOKORO_SETTINGS["lang"]
            }
        }
        
        return {
            "scene_audios": scene_audios,
            "combined_audio": combined_audio,
            "metadata": metadata
        }
    
    def test(self) -> bool:
        """Test the scene audio generator"""
        logger.info("[SceneAudioGenerator] Running tests...")
        
        try:
            # Create test scenes
            test_scenes = [
                {
                    "scene_number": 1,
                    "narration_text": "This is a test narration for scene one. It should be converted to audio successfully."
                },
                {
                    "scene_number": 2,
                    "narration_text": "This is a test narration for scene two. It should also work perfectly."
                }
            ]
            
            # Process test scenes
            result = self.process_scenes(test_scenes)
            
            # Verify results
            if "scene_audios" not in result:
                raise ValueError("Missing scene_audios in result")
            
            if "combined_audio" not in result:
                raise ValueError("Missing combined_audio in result")
            
            if len(result["scene_audios"]) != 2:
                raise ValueError("Expected 2 scene audios")
            
            # Check if audio files exist
            for scene_audio in result["scene_audios"]:
                audio_path = Path(scene_audio["audio_file"])
                if not audio_path.exists():
                    raise ValueError(f"Audio file not found: {audio_path}")
            
            final_audio_path = Path(result["combined_audio"]["final_audio_file"])
            if not final_audio_path.exists():
                raise ValueError(f"Final audio file not found: {final_audio_path}")
            
            logger.info(f"[SceneAudioGenerator] Test passed - generated {len(result['scene_audios'])} scene audios")
            return True
            
        except Exception as e:
            logger.error(f"[SceneAudioGenerator] Test failed: {str(e)}")
            return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the generator
    generator = SceneAudioGenerator()
    
    if generator.test():
        print("✅ SceneAudioGenerator test passed!")
    else:
        print("❌ SceneAudioGenerator test failed!") 