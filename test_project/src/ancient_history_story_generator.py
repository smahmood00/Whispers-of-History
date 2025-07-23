import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import time
from datetime import datetime

from google import genai
from google.genai import types

from .config import (
    GEMINI_API_KEYS,
    STORY_MODEL,
    FILE_PATTERNS,
    BEDTIME_SETTINGS
)
from .base import BaseComponent
from .utils import retry_with_backoff, rate_limiter

logger = logging.getLogger(__name__)

class AncientHistoryStoryGenerator(BaseComponent):
    """Generates ancient history bedtime stories for the Whispers of History channel"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self._setup_api()
        
    def _setup_api(self) -> None:
        """Setup Gemini API with first available key"""
        for api_key in GEMINI_API_KEYS:
            try:
                self.client = genai.Client(api_key=api_key)
                logger.info("Successfully initialized Gemini API")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize with key: {str(e)}")
        raise RuntimeError("Failed to initialize Gemini API with any key")
        
    def _create_outline_prompt(self, user_prompt: str) -> str:
        """Create prompt for master outline generation
        
        Args:
            user_prompt: Historical topic
            
        Returns:
            Prompt string
        """
        total_chapters = BEDTIME_SETTINGS["target_word_count"] // 1000
        scenes_per_chapter = BEDTIME_SETTINGS["scenes_per_chapter"]
        
        return f"""
        You are an expert historian and master storyteller specializing in ancient history for the YouTube channel "Whispers of History".
        
        Create a detailed outline for a {total_chapters}-chapter bedtime story about {user_prompt}.
        The story should be historically accurate but calming and engaging for bedtime listening.
        
        Each chapter will be exactly 1000 words and contain {scenes_per_chapter} scenes.
        
        TONE AND STYLE GUIDELINES:

        1. SOOTHING NARRATIVE VOICE
        Speak slowly and softly, as if you're sharing a secret by candlelight, inviting the listener into a calm, cozy space.
        Let your words flow gently, without sudden shifts, like a slow, steady heartbeat guiding them toward rest.
        Use subtle pauses and a warm, intimate tone that feels like a quiet conversation beside someone's bed.

        2. SENSORY-RICH DESCRIPTIONS
        Describe historical settings through the five senses to create immersive, dreamlike scenes.
        Use soft, calming imagery — flickering torchlight, the scent of parchment, footsteps echoing on ancient stone.
        Focus on gentle details that slowly unfold in the listener's imagination, like a quiet story whispered in the dark.

        3. BALANCED HISTORICAL ACCURACY
        Let history gently reveal itself through feelings and small moments, like discovering a hidden treasure without rushing.
        Avoid overwhelming the listener with names or dates — focus on the mood and atmosphere of the time.
        Anchor the story in human experiences — awe, hope, fear, and wonder — to keep it alive and restful.

        4. THOUGHTFUL PACING
        Begin with soft, slow scene-setting that wraps around the listener like a warm blanket.
        Allow stories to breathe and unfold at their own gentle pace, helping the listener drift along with them.
        Introduce quiet tension or soft drama, emphasizing feelings and choices, not action or urgency.
        End each segment with a reflective, peaceful tone that encourages rest and reflection.

        5. LANGUAGE CHOICES
        Use words that flow like a lullaby, simple yet rich, carrying the listener softly through each story.
        Choose language that feels like a gentle melody, avoiding heavy or academic terms.
        Repeat soothing phrases or motifs gently, like a soft chant.
        Avoid harsh sounds or abrupt expressions that might disturb the calm mood.

        6. EMOTIONAL RESONANCE
        Bring out the quiet emotions that connect us across time — hope, longing, courage, and peace.
        Introduce gentle drama through personal dilemmas, inner conflict, or unspoken choices.
        When conflict arises, focus on strategy, silence, or resolution rather than violence.
        Let listeners feel like they're sharing in a sacred moment, held gently by the stories.
        
        Return a JSON object with this structure:
        {{
          "story_title": "Compelling title for the ancient history story",
          "video_title": "🌙 [Topic]: [Intriguing Subtitle] | Whispers of History",
          "video_description": "SEO-optimized description with timestamps and tags",
          "thumbnail_description": "Detailed prompt for thumbnail image generation",
          "historical_context": "Brief historical context for the story",
          "total_chapters": {total_chapters},
          "chapter_outlines": [
            {{
              "chapter_number": 1,
              "chapter_title": "Title for Chapter 1",
              "historical_setting": "Time period and location",
              "key_events": ["Event 1", "Event 2", "Event 3"],
              "historical_facts": ["Fact 1", "Fact 2"],
              "emotional_tone": "Contemplative, awe-inspiring"
            }},
            ...
          ]
        }}
        """

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    @rate_limiter(calls=1, period=6.0)
    def _generate_outline(self, prompt: str) -> Dict[str, Any]:
        """Generate the master outline with retry logic
        
        Args:
            prompt: Outline generation prompt
            
        Returns:
            Parsed JSON response
        """
        try:
            logger.info("Generating ancient history story outline...")
            
            response = self.client.models.generate_content(
                model=STORY_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            
            return self._clean_and_parse_json(response.text)
            
        except Exception as e:
            logger.error(f"Failed to generate outline: {str(e)}")
            raise
            
    def _create_chapter_prompt(self, chapter_num: int,
                             chapter_outline: Dict[str, Any],
                             previous_chapters: List[Dict[str, Any]]) -> str:
        """Create prompt for chapter generation
        
        Args:
            chapter_num: Chapter number
            chapter_outline: Outline for this chapter
            previous_chapters: List of previously generated chapters
            
        Returns:
            Prompt string
        """
        # Build context from previous chapters
        context = ""
        if previous_chapters:
            context += "Previous chapters summary:\n"
            for prev_chapter in previous_chapters:
                context += f"- Chapter {prev_chapter['chapter_number']}: {prev_chapter['chapter_title']}\n"
                # Add last scene for continuity
                if prev_chapter['scenes']:
                    last_scene = prev_chapter['scenes'][-1]
                    context += f"  Ended with: {last_scene['narration_text'][-200:]}\n"
        else:
            context = "This is the beginning of the story."
        
        # Determine if this is the first or last chapter
        is_first_chapter = chapter_num == 1
        is_last_chapter = chapter_num == chapter_outline.get("total_chapters", 8)
        
        # Special instructions based on chapter position
        chapter_position_instructions = ""
        if is_first_chapter:
            chapter_position_instructions = """
            This is the FIRST chapter of the story. Begin with an engaging, evocative hook that draws the listener in.
            Start with sensory details or an intriguing historical moment that captures attention.
            Do NOT use phrases like "Close your eyes, little one" or similar bedtime story framing devices.
            Instead, begin with vivid historical imagery or an interesting fact that immediately transports the listener to the time period.
            """
        elif is_last_chapter:
            chapter_position_instructions = """
            This is the LAST chapter of the story. The chapter should build toward a satisfying conclusion.
            Only in the final scene, you may end with a gentle closing like "Sleep well..." if appropriate.
            Ensure the ending provides closure while maintaining the soothing, reflective tone.
            """
        else:
            chapter_position_instructions = """
            This is a MIDDLE chapter of the story. It should flow naturally from the previous chapters.
            Do NOT use phrases like "Close your eyes, little one" or "Sleep well, little one" - these are only for the beginning of the first chapter and end of the last chapter.
            Begin this chapter by continuing the narrative thread from the previous chapter, maintaining continuity.
            End the chapter with a gentle transition that leads naturally to the next chapter.
            """
        
        scenes_per_chapter = BEDTIME_SETTINGS["scenes_per_chapter"]
        
        return f"""
        You are writing Chapter {chapter_num} of an ancient history bedtime story for the "Whispers of History" YouTube channel.
        
        Chapter Outline:
        {json.dumps(chapter_outline, indent=2)}
        
        {chapter_position_instructions}
        
        TONE AND STYLE GUIDELINES:

        1. SOOTHING NARRATIVE VOICE
        Speak slowly and softly, as if you're sharing a secret by candlelight, inviting the listener into a calm, cozy space.
        Let your words flow gently, without sudden shifts, like a slow, steady heartbeat guiding them toward rest.
        Use subtle pauses and a warm, intimate tone that feels like a quiet conversation beside someone's bed.

        2. SENSORY-RICH DESCRIPTIONS
        Describe historical settings through the five senses to create immersive, dreamlike scenes.
        Use soft, calming imagery — flickering torchlight, the scent of parchment, footsteps echoing on ancient stone.
        Focus on gentle details that slowly unfold in the listener's imagination, like a quiet story whispered in the dark.

        3. BALANCED HISTORICAL ACCURACY
        Let history gently reveal itself through feelings and small moments, like discovering a hidden treasure without rushing.
        Avoid overwhelming the listener with names or dates — focus on the mood and atmosphere of the time.
        Anchor the story in human experiences — awe, hope, fear, and wonder — to keep it alive and restful.

        4. THOUGHTFUL PACING
        Begin with soft, slow scene-setting that wraps around the listener like a warm blanket.
        Allow stories to breathe and unfold at their own gentle pace, helping the listener drift along with them.
        Introduce quiet tension or soft drama, emphasizing feelings and choices, not action or urgency.
        End each segment with a reflective, peaceful tone that encourages rest and reflection.

        5. LANGUAGE CHOICES
        Use words that flow like a lullaby, simple yet rich, carrying the listener softly through each story.
        Choose language that feels like a gentle melody, avoiding heavy or academic terms.
        Repeat soothing phrases or motifs gently, like a soft chant.
        Avoid harsh sounds or abrupt expressions that might disturb the calm mood.

        6. EMOTIONAL RESONANCE
        Bring out the quiet emotions that connect us across time — hope, longing, courage, and peace.
        Introduce gentle drama through personal dilemmas, inner conflict, or unspoken choices.
        When conflict arises, focus on strategy, silence, or resolution rather than violence.
        Let listeners feel like they're sharing in a sacred moment, held gently by the stories.
        
        CHAPTER OPENING SUGGESTIONS (for first chapter only):
        - Begin with an evocative sensory detail: "The scent of cedar incense filled the air as dawn broke over the ancient city..."
        - Start with a historical moment: "As the first rays of sun touched the desert sands, Babylon was already stirring with life..."
        - Open with atmospheric description: "Moonlight bathed the ziggurats in silver, casting long shadows across the silent courtyards..."
        - Begin with a question: "What secrets did the ancient walls of Babylon hold as they stood sentinel over the Euphrates?"
        
        Requirements:
        - Create exactly {scenes_per_chapter} scenes totaling 1000 words
        - Each scene needs narration_text and image_prompt
        - Write in the soothing tone described above
        - Focus on historical accuracy while maintaining narrative flow
        - Ensure emotional resonance and human connection
        - Maintain continuity with previous chapters
        - Avoid repetitive framing devices across chapters
        
        Previous Story Context:
        {context}
        
        Return a JSON object with this structure:
        {{
          "scenes": [
            {{
              "scene_number": 1,
              "narration_text": "Scene narration text...",
              "image_prompt": "Detailed visual description for image generation..."
            }},
            ...
          ]
        }}
        
        Make sure each scene's image_prompt is a literal, detailed visual description of what's happening in the narration.
        """

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    @rate_limiter(calls=1, period=6.0)
    def _generate_chapter(self, prompt: str) -> Dict[str, Any]:
        """Generate a single chapter with retry logic
        
        Args:
            prompt: Chapter generation prompt
            
        Returns:
            Parsed JSON response
        """
        try:
            logger.info("Generating chapter content...")
            
            response = self.client.models.generate_content(
                model=STORY_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            
            return self._clean_and_parse_json(response.text)
            
        except Exception as e:
            logger.error(f"Failed to generate chapter: {str(e)}")
            raise
            
    def _clean_and_parse_json(self, raw_response: str) -> Dict[str, Any]:
        """Clean and parse JSON response from Gemini
        
        Args:
            raw_response: Raw response string
            
        Returns:
            Parsed JSON data
        """
        try:
            # Find JSON in response
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in response")
                
            json_str = raw_response[json_start:json_end]
            data = json.loads(json_str)
            
            # Check if this is an outline (has chapter_outlines) or chapter (has scenes)
            if "chapter_outlines" in data:
                # This is an outline - validate outline structure
                if "story_title" not in data:
                    logger.warning("Missing 'story_title' in outline response")
                if "video_title" not in data:
                    logger.warning("Missing 'video_title' in outline response")
                if "total_chapters" not in data:
                    logger.warning("Missing 'total_chapters' in outline response")
                    data["total_chapters"] = 8  # Default
            elif "scenes" in data:
                # This is a chapter - validate scene structure
                # Validate each scene has required fields
                for i, scene in enumerate(data["scenes"]):
                    if "scene_number" not in scene:
                        scene["scene_number"] = i + 1
                        
                    if "narration_text" not in scene:
                        if "text" in scene:
                            # Try to use 'text' field if available
                            scene["narration_text"] = scene["text"]
                        else:
                            raise ValueError(f"Missing 'narration_text' field in scene {i+1}")
                        
                    if "image_prompt" not in scene:
                        if "image_description" in scene:
                            # Try to use 'image_description' field if available
                            scene["image_prompt"] = scene["image_description"]
                        else:
                            raise ValueError(f"Missing 'image_prompt' field in scene {i+1}")
            else:
                # Neither outline nor chapter structure recognized
                logger.warning(f"Unexpected JSON structure: {list(data.keys())}")
                # Try to adapt the structure if possible
                if "scenes" not in data and "content" in data and isinstance(data["content"], list):
                    # Some models might return content array instead of scenes
                    data["scenes"] = data["content"]
                    del data["content"]
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise RuntimeError("Invalid JSON response from Gemini")
        except ValueError as e:
            logger.error(f"Invalid JSON structure: {e}")
            raise RuntimeError(f"Invalid JSON structure: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            raise

    def _calculate_story_stats(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistics about the generated story
        
        Args:
            story_data: Parsed story JSON data
            
        Returns:
            Dictionary with story statistics
        """
        total_words = 0
        scene_word_counts = []
        
        # Calculate from scenes
        for scene in story_data.get('scenes', []):
            word_count = len(scene['narration_text'].split())
            scene_word_counts.append(word_count)
            total_words += word_count
        
        return {
            "total_words": total_words,
            "scene_count": len(story_data.get('scenes', [])),
            "chapter_count": len(story_data.get('chapters', [])),
            "scene_word_counts": scene_word_counts,
            "avg_words_per_scene": total_words / len(scene_word_counts) if scene_word_counts else 0,
            "target_total_words": BEDTIME_SETTINGS["target_word_count"],
            "word_count_ratio": total_words / BEDTIME_SETTINGS["target_word_count"] if BEDTIME_SETTINGS["target_word_count"] else 0
        }
        
    def process(self, user_prompt: str, **kwargs) -> Dict[str, Any]:
        """Process a user prompt to generate a complete ancient history story
        
        Args:
            user_prompt: User's historical topic prompt
            
        Returns:
            Dict with story data and metadata
        """
        logger.info(f"Generating ancient history story for: {user_prompt}")
        
        try:
            # Stage 1: Generate master outline
            outline_prompt = self._create_outline_prompt(user_prompt)
            outline = self._generate_outline(outline_prompt)
            
            # Save outline to file
            timestamp = self.get_timestamp()
            outline_file = self.output_dir / f"story_outline_{timestamp}.json"
            with open(outline_file, "w", encoding="utf-8") as f:
                json.dump(outline, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Story outline saved to: {outline_file}")
            
            # Stage 2: Initialize story data with metadata
            story_data = {
                "video_title": outline["video_title"],
                "video_description": outline["video_description"],
                "thumbnail_description": outline["thumbnail_description"],
                "total_words": BEDTIME_SETTINGS["target_word_count"],
                "total_chapters": outline["total_chapters"],
                "chapters": [],
                "scenes": []  # Flattened scenes array
            }
            
            # Stage 3: Generate chapters sequentially
            global_scene_counter = 1
            for chapter_num in range(1, outline["total_chapters"] + 1):
                chapter_outline = outline["chapter_outlines"][chapter_num - 1]
                # Add total chapters to chapter outline for context
                chapter_outline["total_chapters"] = outline["total_chapters"]
                
                logger.info(f"Generating Chapter {chapter_num}: {chapter_outline['chapter_title']}")
                
                # Generate chapter with context from previous chapters
                chapter_prompt = self._create_chapter_prompt(
                    chapter_num,
                    chapter_outline,
                    story_data["chapters"]
                )
                
                chapter_data = self._generate_chapter(chapter_prompt)
                
                # Format chapter data
                chapter = {
                    "chapter_number": chapter_num,
                    "chapter_title": chapter_outline["chapter_title"],
                    "scenes": []
                }
                
                # Process scenes
                for i, scene in enumerate(chapter_data["scenes"], 1):
                    scene_data = {
                        "scene_number": i,
                        "narration_text": scene["narration_text"],
                        "image_prompt": scene["image_prompt"],
                        "chapter_number": chapter_num
                    }
                    chapter["scenes"].append(scene_data)
                    
                    # Add to flattened scenes array with global numbering
                    flattened_scene = scene_data.copy()
                    flattened_scene["scene_number"] = global_scene_counter
                    story_data["scenes"].append(flattened_scene)
                    global_scene_counter += 1
                
                story_data["chapters"].append(chapter)
                
                # Save progress after each chapter
                story_file = self.output_dir / FILE_PATTERNS["story"].format(timestamp=timestamp)
                with open(story_file, "w", encoding="utf-8") as f:
                    json.dump(story_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Chapter {chapter_num} generated and saved")
                
            # Calculate statistics
            stats = self._calculate_story_stats(story_data)
            
            # Final save
            story_file = self.output_dir / FILE_PATTERNS["story"].format(timestamp=timestamp)
            with open(story_file, "w", encoding="utf-8") as f:
                json.dump(story_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Ancient history story saved to: {story_file}")
            
            return {
                "story_data": story_data,
                "story_file": str(story_file),
                "outline_file": str(outline_file),
                "metadata": {
                    "statistics": stats,
                    "timestamp": timestamp,
                    "outline": outline  # Include outline in metadata
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate ancient history story: {e}")
            raise
            
    def test(self) -> bool:
        """Test the ancient history story generator
        
        Returns:
            True if test passes, False otherwise
        """
        logger.info("[AncientHistoryStoryGenerator] Running tests...")
        
        try:
            # Test with a simple prompt
            test_prompt = "Ancient Egypt"
            result = self.process(test_prompt)
            
            if result and "story_data" in result and "metadata" in result:
                stats = result["metadata"]["statistics"]
                logger.info(f"Test successful! Generated story with {stats['scene_count']} scenes")
                logger.info(f"Total words: {stats['total_words']}, Target: {stats['target_total_words']}")
                logger.info(f"Story file: {result['story_file']}")
                logger.info(f"Outline file: {result['outline_file']}")
                return True
            else:
                logger.error("Test failed: Incomplete result")
                return False
                
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            return False 