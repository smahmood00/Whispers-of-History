#!/usr/bin/env python3
"""
Integration script for the Ancient History Story Generator
This shows how to integrate the generator with the existing pipeline
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline_integration.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to demonstrate pipeline integration"""
    parser = argparse.ArgumentParser(description='Integrate Ancient History Story Generator with the pipeline')
    parser.add_argument('--prompt-name', type=str, required=True,
                        help='Name of the prompt file in the prompts/ directory (without .txt extension)')
    parser.add_argument('--output-dir', type=str, default='OUTPUT',
                        help='Base output directory')
    parser.add_argument('--run-full-pipeline', action='store_true',
                        help='Run the full pipeline including image generation, audio, etc.')
    
    args = parser.parse_args()
    
    try:
        # Import necessary components
        from src.ancient_history_story_generator import AncientHistoryStoryGenerator
        from src.bedtime_history_pipeline import BedtimeHistoryPipeline
        
        # Read the prompt file
        prompt_file = Path('prompts') / f"{args.prompt_name}.txt"
        if not prompt_file.exists():
            logger.error(f"Prompt file not found: {prompt_file}")
            return 1
            
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_content = f.read().strip()
            
        logger.info(f"Read prompt: {prompt_content[:100]}...")
        
        # Create output directory
        output_path = Path(args.output_dir) / args.prompt_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Option 1: Run only the story generator
        if not args.run_full_pipeline:
            logger.info("Running only the Ancient History Story Generator...")
            
            # Initialize the generator
            generator = AncientHistoryStoryGenerator(output_dir=output_path)
            
            # Generate the story
            result = generator.process(prompt_content)
            
            # Log results
            stats = result["metadata"]["statistics"]
            logger.info("=" * 50)
            logger.info("Story generation completed!")
            logger.info(f"Story title: {result['story_data']['video_title']}")
            logger.info(f"Total chapters: {stats['chapter_count']}")
            logger.info(f"Total scenes: {stats['scene_count']}")
            logger.info(f"Total words: {stats['total_words']} (target: {stats['target_total_words']})")
            logger.info(f"Story file: {result['story_file']}")
            logger.info(f"Outline file: {result['outline_file']}")
            logger.info("=" * 50)
            
        # Option 2: Run the full pipeline with our generator
        else:
            logger.info("Running the full pipeline with Ancient History Story Generator...")
            
            # Create a subclass of BedtimeHistoryPipeline that uses our generator
            class AncientHistoryPipeline(BedtimeHistoryPipeline):
                def __init__(self, prompt_name=None):
                    super().__init__(prompt_name)
                    # Replace the story generator with our implementation
                    self.story_generator = AncientHistoryStoryGenerator(output_dir=self.output_dir)
                    logger.info("Replaced default story generator with Ancient History Story Generator")
            
            # Initialize the pipeline
            pipeline = AncientHistoryPipeline(prompt_name=args.prompt_name)
            
            # Run the pipeline
            result = pipeline.run(prompt_content)
            
            if result["success"]:
                logger.info("=" * 50)
                logger.info("Pipeline completed successfully!")
                logger.info(f"Video file: {result['video_file']}")
                if "youtube_url" in result:
                    logger.info(f"YouTube URL: {result['youtube_url']}")
                logger.info("=" * 50)
            else:
                logger.error(f"Pipeline failed: {result['error']}")
                return 1
        
        return 0
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 