#!/usr/bin/env python3
"""Test script to run the bedtime history pipeline with prompts folder input"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_next_prompt():
    """Get the next unprocessed prompt from prompts folder"""
    prompts_dir = Path(__file__).parent / "prompts"
    progress_file = Path(__file__).parent / "prompt_progress.txt"
    
    # Get all prompt files
    prompt_files = sorted(list(prompts_dir.glob("*.txt")))
    if not prompt_files:
        logger.error("No prompt files found in prompts/ directory")
        return None, None
    
    # Get processed prompts
    processed_prompts = []
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            processed_prompts = [line.strip() for line in f if line.strip()]
    
    # Find first unprocessed prompt
    for prompt_file in prompt_files:
        prompt_name = prompt_file.stem
        if prompt_name not in processed_prompts:
            # Read the prompt content
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_content = f.read().strip()
            
            return prompt_name, prompt_content
    
    logger.info("🎉 All prompts have been processed!")
    return None, None

def mark_prompt_as_processed(prompt_name):
    """Mark a prompt as processed"""
    progress_file = Path(__file__).parent / "prompt_progress.txt"
    
    # Read existing processed prompts
    processed_prompts = []
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            processed_prompts = [line.strip() for line in f if line.strip()]
    
    # Add new prompt
    processed_prompts.append(prompt_name)
    
    # Write updated list
    with open(progress_file, 'w') as f:
        for p in processed_prompts:
            f.write(f"{p}\n")
    
    logger.info(f"✅ Marked '{prompt_name}' as processed")

def get_status():
    """Get current processing status"""
    prompts_dir = Path(__file__).parent / "prompts"
    progress_file = Path(__file__).parent / "prompt_progress.txt"
    
    # Get all prompts
    prompt_files = sorted(list(prompts_dir.glob("*.txt")))
    all_prompts = [f.stem for f in prompt_files]
    
    # Get processed prompts
    processed_prompts = []
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            processed_prompts = [line.strip() for line in f if line.strip()]
    
    # Find next prompt
    next_prompt = None
    for prompt_name in all_prompts:
        if prompt_name not in processed_prompts:
            next_prompt = prompt_name
            break
    
    return {
        "total_prompts": len(all_prompts),
        "processed": len(processed_prompts),
        "remaining": len(all_prompts) - len(processed_prompts),
        "next_prompt": next_prompt,
        "processed_list": processed_prompts
    }

def test_individual_components():
    """Test individual components"""
    logger.info("Testing individual components...")
    
    try:
        # Test audio generator
        from src.scene_audio_generator import SceneAudioGenerator
        audio_gen = SceneAudioGenerator()
        if not audio_gen.test():
            logger.error("Audio generator test failed")
            return False
        
        # Test subtitle generator
        from src.subtitle_generator import SubtitleGenerator
        subtitle_gen = SubtitleGenerator()
        if not subtitle_gen.test():
            logger.error("Subtitle generator test failed")
            return False
        
        # Test video creator
        from src.bedtime_video_creator import BedtimeVideoCreator
        video_creator = BedtimeVideoCreator()
        if not video_creator.test():
            logger.error("Video creator test failed")
            return False
        
        logger.info("✅ All individual components passed!")
        return True
        
    except Exception as e:
        logger.error(f"Component test failed: {e}")
        return False

def run_pipeline():
    """Run the complete pipeline with next prompt"""
    logger.info("Running complete pipeline...")
    
    try:
        from src.bedtime_history_pipeline import BedtimeHistoryPipeline
        
        # Get next unprocessed prompt
        prompt_name, user_prompt = get_next_prompt()
        
        if prompt_name is None or user_prompt is None:
            logger.info("No more prompts to process")
            return False
        
        logger.info(f"📝 Processing prompt: {prompt_name}")
        logger.info(f"📖 Using prompt: {user_prompt[:100]}...")
        
        # Initialize and run pipeline with prompt name
        pipeline = BedtimeHistoryPipeline(prompt_name=prompt_name)
        results = pipeline.run(user_prompt)
        
        if results['success']:
            logger.info("🎉 Pipeline completed successfully!")
            logger.info(f"Video file: {results['video_file']}")
            
            # Mark prompt as processed
            mark_prompt_as_processed(prompt_name)
            
            # Show updated status
            status = get_status()
            logger.info(f"📊 Progress: {status['processed']}/{status['total_prompts']} completed")
            
            if status['remaining'] > 0:
                logger.info(f"⏭️  Next prompt: {status['next_prompt']}")
            else:
                logger.info("🎉 All prompts completed!")
            
            return True
        else:
            logger.error("❌ Pipeline failed")
            return False
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    logger.info("🚀 Starting bedtime history pipeline test...")
    
    # Show current status
    status = get_status()
    logger.info(f"📊 Status: {status['processed']}/{status['total_prompts']} completed")
    
    if status['remaining'] == 0:
        logger.info("🎉 All prompts have been processed!")
        logger.info("💡 To start over, delete prompt_progress.txt file")
        return True
    
    logger.info(f"🎬 Generating video for next prompt: {status['next_prompt']}")
    
    # Test individual components first
    if not test_individual_components():
        logger.error("❌ Component tests failed")
        return False
    
    # Run the complete pipeline
    if not run_pipeline():
        logger.error("❌ Pipeline test failed")
        return False
    
    logger.info("🎉 Pipeline completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 