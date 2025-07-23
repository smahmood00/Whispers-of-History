"""Main pipeline for automated bedtime history video creation"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Replace BedtimeStoryGenerator with AncientHistoryStoryGenerator
from .ancient_history_story_generator import AncientHistoryStoryGenerator
from .bedtime_image_generator import BedtimeImageGenerator
from .scene_audio_generator import SceneAudioGenerator
from .subtitle_generator import SubtitleGenerator
from .bedtime_video_creator import BedtimeVideoCreator
from .youtube_uploader import YouTubeUploader
from .thumbnail_generator import ThumbnailGenerator
from .config import OUTPUT_DIR, FILE_PATTERNS
from .utils import file_manager

logger = logging.getLogger(__name__)

class BedtimeHistoryPipeline:
    """Main pipeline for bedtime history video creation"""
    
    def __init__(self, prompt_name: Optional[str] = None):
        """Initialize pipeline components
        
        Args:
            prompt_name: Optional name of the prompt being processed
        """
        self.prompt_name = prompt_name or "default"
        self.output_dir = Path(OUTPUT_DIR) / self.prompt_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components - Replace BedtimeStoryGenerator with AncientHistoryStoryGenerator
        self.story_generator = AncientHistoryStoryGenerator(output_dir=self.output_dir)
        self.thumbnail_generator = ThumbnailGenerator(output_dir=self.output_dir)
        self.image_generator = BedtimeImageGenerator(output_dir=self.output_dir)
        self.audio_generator = SceneAudioGenerator(output_dir=self.output_dir)
        self.subtitle_generator = SubtitleGenerator(output_dir=self.output_dir)
        self.video_creator = BedtimeVideoCreator(output_dir=self.output_dir)
        self.youtube_uploader = YouTubeUploader()  # No output_dir needed for YouTube uploader
        
        logger.info(f"All pipeline components initialized successfully in {self.output_dir}!")

    def run(self, prompt: str) -> Dict[str, Any]:
        """Run the complete pipeline
        
        Args:
            prompt: User prompt for story generation
            
        Returns:
            Dictionary with pipeline results and metadata
        """
        try:
            logger.info("🌙 Starting Bedtime History Video Creation Pipeline...")
            logger.info("=" * 60)
            logger.info(f"📖 Prompt: {prompt[:100]}...")
            
            # Step 1: Generate bedtime story
            logger.info("🎭 Step 1: Generating bedtime story...")
            story_result = self.story_generator.process(prompt)
            
            if not story_result or "story_data" not in story_result:
                raise RuntimeError("Story generation failed")
            
            story_data = story_result["story_data"]
            metadata = story_result["metadata"]
            
            logger.info(f"✅ Generated story with {metadata['statistics']['scene_count']} scenes")
            logger.info(f"📊 Story stats: {metadata['statistics']['total_words']} words")
            
            # Step 2: Generate thumbnail for YouTube
            logger.info("🖼️ Step 2: Generating YouTube thumbnail...")
            thumbnail_result = self.thumbnail_generator.process(story_result)
            
            if not thumbnail_result or not thumbnail_result.get("success", False):
                logger.warning("Thumbnail generation failed, proceeding without custom thumbnail")
                thumbnail_file = None
            else:
                thumbnail_file = thumbnail_result["thumbnail_file"]
                logger.info(f"✅ Generated YouTube thumbnail: {thumbnail_file}")
            
            # Step 3: Generate scene images
            logger.info("🎨 Step 3: Generating scene images...")
            image_result = self.image_generator.process_scenes(story_data["scenes"])
            
            if not image_result:
                raise RuntimeError("Image generation failed")
                
            logger.info(f"✅ Generated {len(image_result['images'])} scene images")
            
            # Step 4: Generate scene audio
            logger.info("🎵 Step 4: Generating scene audio...")
            audio_result = self.audio_generator.process_scenes(story_data["scenes"])
            
            if not audio_result or "combined_audio" not in audio_result:
                raise RuntimeError("Audio generation failed")
                
            logger.info(f"✅ Generated {len(audio_result['scene_audios'])} scene audio files")
            logger.info(f"📊 Total audio duration: {audio_result['metadata']['total_duration']:.2f}s")
            
            # Step 5: Generate subtitles
            logger.info("💬 Step 5: Generating subtitles...")
            subtitle_result = self.subtitle_generator.process_audio(Path(audio_result["combined_audio"]["final_audio_file"]))
            
            if not subtitle_result:
                raise RuntimeError("Subtitle generation failed")
                
            logger.info(f"✅ Generated subtitles with {subtitle_result['metadata']['segment_count']} segments")
            
            # Step 6: Create final video
            logger.info("🎬 Step 6: Creating final video...")
            video_result = self.video_creator.process_bedtime_video(
                images=image_result["images"],
                scene_durations=[audio["duration"] for audio in audio_result["scene_audios"]],
                final_audio_path=Path(audio_result["combined_audio"]["final_audio_file"]),
                subtitle_path=Path(subtitle_result["subtitle_file"])
            )
            
            if not video_result or "metadata" not in video_result:
                raise RuntimeError("Video creation failed")
                
            logger.info(f"✅ Created video: {video_result['video_file']}")
            logger.info(f"📊 Video duration: {video_result['metadata']['duration']:.2f}s")
            
            # Step 7: Upload to YouTube with thumbnail
            logger.info("📺 Step 7: Uploading to YouTube...")
            upload_result = self.youtube_uploader.upload_video_with_thumbnail(
                video_file=video_result["video_file"],
                title=story_data["video_title"],
                description=story_data["video_description"],
                thumbnail_file=thumbnail_file
            )
            
            if not upload_result:
                raise RuntimeError("YouTube upload failed")
                
            logger.info(f"✅ Uploaded video: {upload_result['video_url']}")
            if "thumbnail_url" in upload_result:
                logger.info(f"✅ Set custom thumbnail: {upload_result['thumbnail_url']}")
            
            # Save pipeline metadata
            metadata = {
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "prompt": prompt,
                "story": story_result,
                "thumbnail": thumbnail_result if thumbnail_file else {"success": False, "error": "No thumbnail generated"},
                "images": image_result,
                "audio": audio_result,
                "subtitles": subtitle_result,
                "video": video_result,
                "youtube": upload_result
            }
            
            metadata_file = self.output_dir / FILE_PATTERNS["pipeline_metadata"].format(
                timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("✨ Bedtime video creation successful!")
            
            return {
                "success": True,
                "video_file": video_result["video_file"],
                "youtube_url": upload_result["video_url"],
                "thumbnail_file": thumbnail_file,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            logger.error("💔 Bedtime video creation unsuccessful")
            
            # Save error metadata
            error_metadata = {
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "prompt": prompt,
                "error": str(e)
            }
            
            error_file = self.output_dir / FILE_PATTERNS["pipeline_metadata_error"].format(
                timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            
            with open(error_file, "w") as f:
                json.dump(error_metadata, f, indent=2)
                
            logger.info(f"Pipeline metadata saved to: {error_file}")
            
            return {
                "success": False,
                "error": str(e),
                "metadata": error_metadata
            }
    
    def test_all_components(self) -> bool:
        """Test all pipeline components
        
        Returns:
            True if all tests pass, False otherwise
        """
        logger.info("🧪 Testing all bedtime history pipeline components...")
        
        components = [
            ("Story Generator", self.story_generator),
            ("Thumbnail Generator", self.thumbnail_generator),
            ("Image Generator", self.image_generator),
            ("Audio Generator", self.audio_generator),
            ("Subtitle Generator", self.subtitle_generator),
            ("Video Creator", self.video_creator),
            ("YouTube Uploader", self.youtube_uploader)
        ]
        
        all_passed = True
        for name, component in components:
            try:
                logger.info(f"Testing {name}...")
                if component.test():
                    logger.info(f"✅ {name} test passed")
                else:
                    logger.error(f"❌ {name} test failed")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {name} test error: {str(e)}")
                all_passed = False
        
        if all_passed:
            logger.info("🎉 All component tests passed!")
        else:
            logger.error("💔 Some component tests failed")
        
        return all_passed
    
    def cleanup(self) -> None:
        """Cleanup any resources"""
        logger.info("🧹 Cleaning up pipeline resources...")
        for component in [self.story_generator, self.thumbnail_generator, self.image_generator, 
                         self.audio_generator, self.subtitle_generator, self.video_creator, 
                         self.youtube_uploader]:
            if hasattr(component, 'cleanup'):
                component.cleanup()

if __name__ == "__main__":
    # Configure logging for better output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("bedtime_pipeline.log")
        ]
    )
    
    # Get user prompt
    logger.info("🚀 Starting direct pipeline run...")
    prompt = input("Please enter a story prompt: ")
    
    # Create a prompt name from the first few words of the prompt or timestamp
    if prompt:
        # Use first 3 words of prompt, lowercase with underscores
        words = prompt.split()[:3]
        prompt_name = "_".join(word.lower() for word in words if word.isalnum())
        if not prompt_name:  # If no valid words were found
            prompt_name = f"direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        prompt_name = f"direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create and run pipeline
    pipeline = BedtimeHistoryPipeline(prompt_name=prompt_name)
    
    try:
        # Test all components first
        logger.info("🔍 Running component tests...")
        if not pipeline.test_all_components():
            logger.error("❌ Component tests failed, aborting pipeline")
            exit(1)
        
        # Run the full pipeline
        logger.info(f"🚀 Processing prompt as '{prompt_name}'...")
        result = pipeline.run(prompt)
        
        if result["success"]:
            print("\n" + "="*60)
            print("🌟 BEDTIME HISTORY VIDEO CREATED SUCCESSFULLY! 🌟")
            print("="*60)
            print(f"📺 Video: {result['video_file']}")
            print(f"🌐 YouTube: {result['youtube_url']}")
            if "thumbnail_file" in result and result["thumbnail_file"]:
                print(f"🖼️ Thumbnail: {result['thumbnail_file']}")
            print(f"📊 Duration: {result['metadata']['video']['duration']:.2f}s")
            print(f"🎬 Scenes: {len(result['metadata']['story']['story_data']['scenes'])}")
            print("🌙 Sweet dreams! 🌙")
        else:
            print(f"\n❌ Pipeline failed: {result['error']}")
            
    except KeyboardInterrupt:
        logger.info("🛑 Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
    finally:
        pipeline.cleanup() 