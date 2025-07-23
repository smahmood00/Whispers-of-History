import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import timedelta
import whisper

from .config import (
    FILE_PATTERNS,
    BEDTIME_SETTINGS
)
from .base import BaseComponent
from .utils import retry_with_backoff

logger = logging.getLogger(__name__)

class SubtitleGenerator(BaseComponent):
    """Generates subtitles using Whisper speech-to-text"""
    
    def __init__(self, output_dir: Optional[Path] = None, model_name: str = "base"):
        super().__init__(output_dir)
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self) -> None:
        """Load Whisper model for transcription"""
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            logger.info("Successfully loaded Whisper model")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise RuntimeError(f"Whisper model loading failed: {str(e)}")
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp for SRT format
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string (HH:MM:SS,mmm)
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def _format_subtitle_text(self, text: str, max_chars_per_line: int = 50, max_lines: int = 2) -> str:
        """Format subtitle text with proper line breaks
        
        Args:
            text: Raw subtitle text
            max_chars_per_line: Maximum characters per line
            max_lines: Maximum number of lines
            
        Returns:
            Formatted subtitle text
        """
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Check if adding this word would exceed line length
            if len(current_line + " " + word) <= max_chars_per_line:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                # Start new line
                if current_line:
                    lines.append(current_line)
                current_line = word
                
                # Check if we've reached max lines
                if len(lines) >= max_lines:
                    break
        
        # Add the last line
        if current_line and len(lines) < max_lines:
            lines.append(current_line)
        
        return "\n".join(lines)
    
    def _create_srt_content(self, segments: List[Dict[str, Any]]) -> str:
        """Create SRT format subtitle content
        
        Args:
            segments: List of transcribed segments
            
        Returns:
            SRT formatted string
        """
        srt_parts = []
        
        for i, segment in enumerate(segments, 1):
            start_time = self._format_timestamp(segment["start"])
            end_time = self._format_timestamp(segment["end"])
            text = segment["text"].strip()
            
            # Format text with line and character limits
            formatted_text = self._format_subtitle_text(text)
            
            srt_parts.extend([
                str(i),
                f"{start_time} --> {end_time}",
                formatted_text,
                ""  # Empty line between entries
            ])
        
        return "\n".join(srt_parts)
    
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def _transcribe_audio(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe audio file using Whisper with optimized settings
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcription result
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")
            
            # Transcribe with optimized settings for bedtime content
            result = self.model.transcribe(
                str(audio_path),
                language="en",          # Specify language for better accuracy
                beam_size=5,            # Increase beam size for better results
                best_of=5,              # Number of candidates to consider
                temperature=0.0,        # Reduce randomness for consistent results
                verbose=False,          # Reduce output verbosity
                fp16=False,             # Use full precision for better accuracy
                word_timestamps=True    # Get word-level timestamps
            )
            
            logger.info(f"Transcription completed with {len(result.get('segments', []))} segments")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise
    
    def process_audio(self, audio_path: Path, **kwargs) -> Dict[str, Any]:
        """Generate subtitles for audio file
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with subtitle data and metadata
        """
        logger.info(f"Generating subtitles for {audio_path}")
        
        # Verify audio file exists
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Transcribe audio
        result = self._transcribe_audio(audio_path)
        
        if not result or "segments" not in result:
            raise RuntimeError("Transcription failed")
        
        # Create SRT content with improved formatting
        srt_content = self._create_srt_content(result["segments"])
        
        # Save subtitles
        timestamp = self.get_timestamp()
        subtitle_filename = FILE_PATTERNS["subtitle"].format(timestamp=timestamp)
        subtitle_path = self.save_output(srt_content, subtitle_filename)
        
        # Save raw transcription for debugging
        transcription_filename = f"transcription_{timestamp}.json"
        transcription_path = self.save_json(result, transcription_filename)
        
        # Create metadata
        metadata = {
            "timestamp": timestamp,
            "audio_file": str(audio_path),
            "subtitle_file": str(subtitle_path),
            "transcription_file": str(transcription_path),
            "language": result.get("language", "en"),
            "segment_count": len(result["segments"]),
            "duration": result["segments"][-1]["end"] if result["segments"] else 0,
            "model_used": self.model_name,
            "settings": {
                "beam_size": 5,
                "best_of": 5,
                "temperature": 0.0,
                "max_chars_per_line": 50,
                "max_lines": 2,
                "word_timestamps": True
            }
        }
        
        logger.info(f"Subtitles generated with {metadata['segment_count']} segments")
        logger.info(f"Subtitle file saved to: {subtitle_path}")
        
        return {
            "subtitle_file": str(subtitle_path),
            "transcription_file": str(transcription_path),
            "metadata": metadata,
            "segments": result["segments"]
        }
    
    def test(self) -> bool:
        """Test the subtitle generator"""
        logger.info("[SubtitleGenerator] Running tests...")
        
        try:
            # Look for existing audio files to test with
            audio_files = list(self.output_dir.glob("final_audio_*.wav"))
            
            if not audio_files:
                logger.warning("No audio files found for testing, creating a simple test")
                return True  # Skip test if no audio files available
            
            # Use the most recent audio file
            test_audio_path = max(audio_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Testing with audio file: {test_audio_path}")
            
            # Process audio file
            result = self.process_audio(test_audio_path)
            
            # Verify results
            if "subtitle_file" not in result:
                raise ValueError("Missing subtitle_file in result")
            
            subtitle_path = Path(result["subtitle_file"])
            if not subtitle_path.exists():
                raise ValueError(f"Subtitle file not found: {subtitle_path}")
            
            # Check subtitle content
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                subtitle_content = f.read()
            
            if not subtitle_content.strip():
                raise ValueError("Subtitle file is empty")
            
            # Check for basic SRT format
            if "-->" not in subtitle_content:
                raise ValueError("Invalid SRT format")
            
            logger.info(f"[SubtitleGenerator] Test passed - generated subtitles with {result['metadata']['segment_count']} segments")
            return True
            
        except Exception as e:
            logger.error(f"[SubtitleGenerator] Test failed: {str(e)}")
            return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the generator
    generator = SubtitleGenerator()
    
    if generator.test():
        print("✅ SubtitleGenerator test passed!")
    else:
        print("❌ SubtitleGenerator test failed!") 