import json
import logging
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image

from .config import (
    GEMINI_API_KEYS,
    IMAGE_MODEL,
    FILE_PATTERNS,
    BEDTIME_SETTINGS
)
from .base import BaseComponent
from .utils import retry_with_backoff, rate_limiter

logger = logging.getLogger(__name__)

class BedtimeImageGenerator(BaseComponent):
    """Generates bedtime-appropriate images using Google Gemini API"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self.api_clients = []
        for api_key in GEMINI_API_KEYS:
            client = genai.Client(api_key=api_key)
            self.api_clients.append(client)
        self.current_client_idx = 0
        
        # Optimized settings for bedtime content
        self.max_workers = len(self.api_clients)
        self.batch_size = len(self.api_clients)
        self.batch_delay = 6  # 6 seconds between batches (10 RPM limit)
        
        logger.info(f"Initialized BedtimeImageGenerator with {self.max_workers} API clients")

    def _get_next_client(self) -> genai.Client:
        """Get next available API client using round-robin"""
        client = self.api_clients[self.current_client_idx]
        self.current_client_idx = (self.current_client_idx + 1) % len(self.api_clients)
        return client

    def _enhance_historical_prompt(self, scene: Dict[str, Any]) -> str:
        """Enhance image prompt for vintage-style historical illustrations
        
        Args:
            scene: Scene data with image_prompt
            
        Returns:
            Enhanced prompt optimized for vintage historical illustrations without faces
        """
        base_prompt = scene["image_prompt"]
        
        enhanced_prompt = f"""
        Create a grainy, vintage-style illustration of a historical setting for the "Past Bedtime" YouTube channel:
        
        {base_prompt}
        
        CRITICAL REQUIREMENTS:
        - Silhouettes are acceptable 
        - Vintage-style illustration, not photorealistic
        - Historical setting or artifacts only
        
        STYLE REQUIREMENTS:
        - grainy texture
        - vintage illustration
        - aged paper effect
        - painterly
        - low contrast
        - dreamlike historical atmosphere
        - sepia tones
        - soft lighting / chiaroscuro
        - Blurred edges and slightly faded appearance
        - Muted earth tones, faded parchment browns, dusty grays, and desaturated blues
        - Warm, moody lighting—lit by candles, oil lamps, or filtered sunlight
        - Historical accuracy subtly implied through architecture, objects, or script
        
        ATMOSPHERE REQUIREMENTS:
        - Quiet, slow, and sleep-inducing overall tone
        - Avoid bright colors, sharp contrasts, or modern elements
        - Evoke a sense of timelessness and historical mystery
        - Create a calming, contemplative mood suitable for bedtime viewing
        - Focus on environments, objects, and settings rather than people
        
        TECHNICAL REQUIREMENTS:
        - 16:9 aspect ratio suitable for video
        - Balanced composition with a clear focal point
        - Sufficient detail to be interesting but not overwhelming
        - focus on historical environments and objects
       
        ART STYLE TAGS: grainy texture, vintage illustration, aged paper effect, painterly, low contrast, dreamlike historical atmosphere, sepia tones, soft lighting, chiaroscuro
        """
        
        return enhanced_prompt

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    @rate_limiter(calls=1, period=6.0)
    def _generate_single_image(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a single bedtime image with retry logic and rate limiting
        
        Args:
            scene: Scene data with image_prompt and scene_number
            
        Returns:
            Dictionary with image data and metadata
        """
        client = self._get_next_client()
        start_time = time.time()
        scene_number = scene["scene_number"]
        
        logger.info(f"Generating bedtime image for scene {scene_number}...")

        try:
            # Enhance prompt for bedtime content
            enhanced_prompt = self._enhance_historical_prompt(scene)
            
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                    temperature=0.4,  # Lower temperature for more consistent, calming results
                )
            )

            if not response or not response.candidates or not response.candidates[0].content:
                raise RuntimeError("No image generated")

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

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = FILE_PATTERNS["image"].format(
                scene_number=scene_number,
                timestamp=timestamp
            )
            image_path = self.output_dir / image_filename
            image_data.save(image_path, quality=95, optimize=True)

            generation_time = time.time() - start_time
            logger.info(f"Bedtime image for scene {scene_number} generated in {generation_time:.2f}s")

            metadata = {
                "scene_number": scene_number,
                "image_path": str(image_path),
                "original_prompt": scene["image_prompt"],
                "enhanced_prompt": enhanced_prompt,
                "description": description,
                "timestamp": timestamp,
                "generation_time": generation_time,
                "image_size": image_data.size,
                "bedtime_optimized": True
            }

            return metadata

        except Exception as e:
            logger.error(f"Error generating bedtime image for scene {scene_number}: {str(e)}")
            raise

    async def generate_bedtime_images(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate multiple bedtime images in parallel
        
        Args:
            scenes: List of scene data with image prompts
            
        Returns:
            List of metadata dictionaries for generated images
        """
        logger.info(f"Generating {len(scenes)} bedtime images...")
        
        # Process scenes in parallel batches
        async def process_batch(batch_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for scene in batch_scenes:
                    futures.append(
                        executor.submit(self._generate_single_image, scene)
                    )
                return [f.result() for f in futures]

        # Split scenes into batches and process
        results = []
        for i in range(0, len(scenes), self.batch_size):
            batch = scenes[i:i + self.batch_size]
            batch_results = await process_batch(batch)
            results.extend(batch_results)
            
            # Apply rate limiting between batches
            if i + self.batch_size < len(scenes):
                logger.info(f"Completed batch {i//self.batch_size + 1}, waiting {self.batch_delay}s before next batch...")
                await asyncio.sleep(self.batch_delay)

        return results

    def process_scenes(self, scenes: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Process scenes to generate bedtime-appropriate images
        
        Args:
            scenes: List of scene data with image prompts
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with image generation results and metadata
        """
        logger.info(f"Processing {len(scenes)} scenes for bedtime image generation...")
        
        # Generate images using parallel processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(self.generate_bedtime_images(scenes))
            
            # Calculate statistics
            total_generation_time = sum(result["generation_time"] for result in results)
            avg_generation_time = total_generation_time / len(results) if results else 0
            
            # Create metadata
            metadata = {
                "timestamp": self.get_timestamp(),
                "scene_count": len(scenes),
                "total_generation_time": total_generation_time,
                "avg_generation_time": avg_generation_time,
                "bedtime_optimized": True,
                "style_settings": {
                    "color_palette": "soft_pastels",
                    "atmosphere": "calming_twilight",
                    "style": "storybook_illustration"
                }
            }
            
            return {
                "images": results,
                "metadata": metadata
            }
            
        finally:
            loop.close()

    def test(self) -> bool:
        """Test the bedtime image generator"""
        logger.info("[BedtimeImageGenerator] Running tests...")
        
        try:
            # Create test scenes
            test_scenes = [
                {
                    "scene_number": 1,
                    "image_prompt": "A peaceful moonlit garden with soft flowers and gentle shadows, perfect for bedtime viewing"
                },
                {
                    "scene_number": 2,
                    "image_prompt": "A cozy cottage with warm light glowing from windows, surrounded by sleepy trees"
                }
            ]
            
            # Process test scenes
            result = self.process_scenes(test_scenes)
            
            # Verify results
            if "images" not in result:
                raise ValueError("Missing images in result")
            
            if len(result["images"]) != 2:
                raise ValueError("Expected 2 images")
            
            # Check if image files exist
            for image_result in result["images"]:
                image_path = Path(image_result["image_path"])
                if not image_path.exists():
                    raise ValueError(f"Image file not found: {image_path}")
                
                # Verify bedtime optimization
                if not image_result.get("bedtime_optimized", False):
                    raise ValueError("Image not marked as bedtime optimized")
            
            logger.info(f"[BedtimeImageGenerator] Test passed - generated {len(result['images'])} bedtime images")
            return True
            
        except Exception as e:
            logger.error(f"[BedtimeImageGenerator] Test failed: {str(e)}")
            return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the generator
    generator = BedtimeImageGenerator()
    
    if generator.test():
        print("✅ BedtimeImageGenerator test passed!")
    else:
        print("❌ BedtimeImageGenerator test failed!") 