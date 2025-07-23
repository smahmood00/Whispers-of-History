#!/usr/bin/env python3
"""
Test script for the Ancient History Story Generator
This allows testing the generator independently of the pipeline
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
        logging.FileHandler('ancient_history_generator.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to test the Ancient History Story Generator"""
    parser = argparse.ArgumentParser(description='Test the Ancient History Story Generator')
    parser.add_argument('--topic', type=str, default='Ancient Rome',
                        help='Historical topic to generate a story about')
    parser.add_argument('--output-dir', type=str, default='OUTPUT/ancient_history_test',
                        help='Output directory for generated files')
    parser.add_argument('--test-only', action='store_true',
                        help='Run the built-in test method only')
    
    args = parser.parse_args()
    
    try:
        # Import the generator class
        from src.ancient_history_story_generator import AncientHistoryStoryGenerator
        
        # Create output directory
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize the generator
        generator = AncientHistoryStoryGenerator(output_dir=output_path)
        
        if args.test_only:
            # Run the built-in test method
            logger.info("Running built-in test...")
            success = generator.test()
            if success:
                logger.info("Test completed successfully!")
                return 0
            else:
                logger.error("Test failed!")
                return 1
        else:
            # Generate a story with the provided topic
            logger.info(f"Generating story for topic: {args.topic}")
            result = generator.process(args.topic)
            
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
            
            return 0
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 