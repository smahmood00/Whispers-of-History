import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from io import BytesIO
import json

from google import genai
from google.genai import types
from PIL import Image

from .config import (
    GEMINI_API_KEYS,
    IMAGE_MODEL,
    FILE_PATTERNS
)
from .base import BaseComponent
from .utils import retry_with_backoff, rate_limiter

logger = logging.getLogger(__name__)

class ThumbnailGenerator(BaseComponent):
    """Generates YouTube thumbnails using Google Gemini API"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self._setup_api()
        
    def _setup_api(self) -> None:
        """Setup Gemini API with first available key"""
        for api_key in GEMINI_API_KEYS:
            try:
                self.client = genai.Client(api_key=api_key)
                logger.info("Successfully initialized Gemini API for thumbnail generation")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize with key: {str(e)}")
        raise RuntimeError("Failed to initialize Gemini API with any key")
        
    def _create_thumbnail_prompt(self, thumbnail_description: str, story_outline: Dict[str, Any]) -> str:
        """Create an optimized prompt for YouTube thumbnail generation
        
        Args:
            thumbnail_description: Description for the thumbnail
            story_outline: Complete story outline for context
            
        Returns:
            Enhanced prompt for thumbnail generation
        """
        # Extract useful context from the story outline
        story_title = story_outline.get("story_title", "Ancient History Story")
        video_title = story_outline.get("video_title", "Whispers of History")
        historical_context = story_outline.get("historical_context", "")
        
        # Extract chapter outlines for additional context
        chapter_outlines = story_outline.get("chapter_outlines", [])
        chapter_context = ""
        
        # Include key information from chapter outlines
        if chapter_outlines:
            chapter_context = "CHAPTER THEMES:\n"
            for i, chapter in enumerate(chapter_outlines[:3]):  # Use first 3 chapters for context
                chapter_title = chapter.get("chapter_title", f"Chapter {i+1}")
                setting = chapter.get("historical_setting", "")
                key_events = chapter.get("key_events", [])
                facts = chapter.get("historical_facts", [])
                
                chapter_context += f"- {chapter_title}: {setting}\n"
                
                if key_events:
                    events_text = ", ".join(key_events[:3])  # Limit to 3 key events
                    chapter_context += f"  Events: {events_text}\n"
                
                if facts:
                    facts_text = ", ".join(facts[:2])  # Limit to 2 facts
                    chapter_context += f"  Facts: {facts_text}\n"
        
        # Create a YouTube-optimized thumbnail prompt with full context
        enhanced_prompt = f"""
        Create a captivating YouTube thumbnail for the "Whispers of History" channel's video titled:
        "{video_title}"
        
        THUMBNAIL DESCRIPTION:
        {thumbnail_description}
        
        HISTORICAL CONTEXT:
        {historical_context}
        
        STORY TITLE:
        {story_title}
        
        {chapter_context}
        
        CRITICAL REQUIREMENTS:
        - Create a YOUTUBE THUMBNAIL optimized for click-through rate
        - 16:9 aspect ratio (1280x720 pixels)
        - MUST INCLUDE A HUMAN FIGURE IN SIDE VIEW/PROFILE (not facing camera directly)
        - The human should be in period-appropriate clothing for the historical setting
        - The human figure should be a close-up shot showing head and shoulders or upper body
        - Avoid showing detailed facial features - keep them slightly obscured or in shadow
        - Must be historically themed and visually compelling
        - Should be instantly recognizable as ancient history content
        - Focus on the most visually interesting elements from the story outline
        
        HOOK TEXT REQUIREMENTS:
        - CREATE AND INCLUDE A POWERFUL 3-WORD HOOK DIRECTLY IN THE IMAGE
        - The hook should be catchy, dramatic, and relevant to the historical content
        - Use ALL CAPS for the hook text
        - Examples of good hooks: "EMPIRE RISES AGAIN", "SECRETS OF BABYLON", "PHARAOH'S LAST STAND"
        - The hook should evoke curiosity and emotion
        - The hook should relate to the key themes or events in the story
        
        STYLE REQUIREMENTS:
        - Dramatic lighting with strong contrast
        - Rich, vibrant colors that pop on small screens
        - Clear focal point that draws the eye
        - Vintage/historical aesthetic but with modern visual appeal
        - Cinematic composition with depth
        - Slightly dreamlike/mystical quality
        - Side-lit profile of human figure creating dramatic shadows
        - The hook text should be in a dramatic, bold font (like "Cinzel")
        - Text should be large, clear and readable with high contrast against the background
        - Text placement should be at the bottom of the image with good visual balance
        
        TECHNICAL REQUIREMENTS:
        - High detail and sharpness in the central focal point
        - Balanced composition with visual hierarchy
        - Strong color contrast to stand out in YouTube search results
        - Avoid overly busy backgrounds that distract from the main subject
        - Create visual intrigue that makes viewers want to click
        - The hook text should be integrated directly into the image
        - Text should be in a dramatic serif font, bold, and easily readable
        - Text color should contrast well with the background (white with shadow or glow effect works well)
        
        ART STYLE TAGS: cinematic, dramatic lighting, historical, vibrant colors, high contrast, YouTube thumbnail, eye-catching, professional, human profile, side view, integrated text
        
        IMPORTANT: After generating the image, please describe what 3-word hook text you included in the thumbnail.
        """
        
        return enhanced_prompt

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    @rate_limiter(calls=1, period=6.0)
    def _generate_thumbnail(self, thumbnail_prompt: str) -> Dict[str, Any]:
        """Generate a YouTube thumbnail with retry logic
        
        Args:
            thumbnail_prompt: Enhanced prompt for thumbnail generation
            
        Returns:
            Dictionary with thumbnail data and metadata
        """
        start_time = time.time()
        
        logger.info("Generating YouTube thumbnail...")

        try:
            response = self.client.models.generate_content(
                model=IMAGE_MODEL,
                contents=thumbnail_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                    temperature=0.7,  # Higher temperature for more creative hooks
                )
            )

            if not response or not response.candidates or not response.candidates[0].content:
                raise RuntimeError("No thumbnail generated")

            # Extract image data
            image_data = None
            description = None
            content = response.candidates[0].content
            
            if not hasattr(content, 'parts') or not content.parts:
                raise RuntimeError("Response content has no parts")

            for part in content.parts:
                if hasattr(part, 'text') and part.text is not None:
                    description = part.text
                elif hasattr(part, 'inline_data') and part.inline_data is not None and hasattr(part.inline_data, 'data'):
                    image_bytes = part.inline_data.data
                    if not isinstance(image_bytes, bytes):
                        raise RuntimeError("Invalid image data type")
                    image = Image.open(BytesIO(image_bytes))
                    # Convert to RGB if needed
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image_data = image

            if image_data is None:
                raise RuntimeError("No image data in response")

            # Save thumbnail
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            thumbnail_filename = FILE_PATTERNS["thumbnail"].format(
                timestamp=timestamp
            )
            thumbnail_path = self.output_dir / thumbnail_filename
            image_data.save(thumbnail_path, quality=95, optimize=True)

            generation_time = time.time() - start_time
            logger.info(f"YouTube thumbnail generated in {generation_time:.2f}s")
            
            # Extract the hook text from the model's description
            hook_text = ""
            if description:
                # Look for patterns like "The 3-word hook used is", "I included the hook", etc.
                description_lower = description.lower()
                hook_patterns = [
                    "3-word hook", "three-word hook", "hook text", "hook phrase",
                    "included the text", "text included", "text in the image"
                ]
                
                for pattern in hook_patterns:
                    if pattern in description_lower:
                        # Find sentences containing the pattern
                        sentences = [s.strip() for s in description.split(".")]
                        for sentence in sentences:
                            if pattern in sentence.lower():
                                # Look for text in quotes or all caps words
                                if '"' in sentence:
                                    # Extract text between quotes
                                    start = sentence.find('"')
                                    end = sentence.find('"', start + 1)
                                    if start != -1 and end != -1:
                                        hook_text = sentence[start+1:end].strip()
                                        break
                                else:
                                    # Look for 3 consecutive uppercase words
                                    words = sentence.split()
                                    uppercase_words = [w for w in words if w.isupper() and len(w) > 1]
                                    if len(uppercase_words) >= 3:
                                        hook_text = " ".join(uppercase_words[:3])
                                        break
                    
                    if hook_text:
                        break
                        
                # If still no hook found, look for any 3 consecutive uppercase words in the entire description
                if not hook_text:
                    words = description.split()
                    uppercase_words = [w for w in words if w.isupper() and len(w) > 1]
                    if len(uppercase_words) >= 3:
                        hook_text = " ".join(uppercase_words[:3])
            
            if hook_text:
                logger.info(f"Model-generated hook text: '{hook_text}'")
            else:
                logger.warning("Could not extract hook text from model description")

            metadata = {
                "thumbnail_path": str(thumbnail_path),
                "description": description,
                "timestamp": timestamp,
                "generation_time": generation_time,
                "image_size": image_data.size,
                "hook_text": hook_text
            }

            return metadata

        except Exception as e:
            logger.error(f"Error generating YouTube thumbnail: {str(e)}")
            raise

    def process(self, story_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Process story result to generate a YouTube thumbnail
        
        Args:
            story_result: Result from story generation step
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with thumbnail generation results and metadata
        """
        try:
            # Extract thumbnail description and story outline
            story_data = story_result.get("story_data", {})
            metadata = story_result.get("metadata", {})
            
            # Get the full story outline from metadata
            outline = metadata.get("outline", {})
            
            # If outline is empty, try to load it from the outline file
            if not outline and "outline_file" in story_result:
                try:
                    outline_file = story_result["outline_file"]
                    logger.info(f"Loading story outline from {outline_file}")
                    with open(outline_file, "r", encoding="utf-8") as f:
                        outline = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load outline file: {e}")
            
            # If still no outline, use story data
            if not outline:
                outline = story_data
            
            thumbnail_description = story_data.get("thumbnail_description", "")
            if not thumbnail_description:
                logger.warning("No thumbnail description found, using default")
                thumbnail_description = "Ancient history scene for YouTube thumbnail"
            
            # Create enhanced prompt with full outline context
            thumbnail_prompt = self._create_thumbnail_prompt(thumbnail_description, outline)
            
            # Generate thumbnail
            thumbnail_result = self._generate_thumbnail(thumbnail_prompt)
            
            # Return result
            return {
                "success": True,
                "thumbnail_file": thumbnail_result["thumbnail_path"],
                "metadata": {
                    "description": thumbnail_result["description"],
                    "generation_time": thumbnail_result["generation_time"],
                    "timestamp": thumbnail_result["timestamp"],
                    "image_size": thumbnail_result["image_size"],
                    "hook_text": thumbnail_result.get("hook_text", "")
                }
            }
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def test(self) -> bool:
        """Test the thumbnail generator
        
        Returns:
            True if test passes, False otherwise
        """
        logger.info("[ThumbnailGenerator] Running tests...")
        
        try:
            # Create a simple test prompt
            test_prompt = """
            Create a YouTube thumbnail for an ancient history video about the Roman Empire.
            The thumbnail should feature ancient Roman architecture with dramatic lighting.
            """
            
            # Generate a test thumbnail
            result = self._generate_thumbnail(test_prompt)
            
            if result and "thumbnail_path" in result:
                logger.info(f"Test successful! Generated thumbnail: {result['thumbnail_path']}")
                return True
            else:
                logger.error("Test failed: Incomplete result")
                return False
                
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            return False 