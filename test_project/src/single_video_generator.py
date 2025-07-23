import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SingleVideoGenerator:
    def __init__(self, prompts_dir="prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(exist_ok=True)
        self.progress_file = "prompt_progress.txt"
    
    def get_all_prompts(self):
        """Get all prompts in alphabetical order"""
        prompt_files = sorted(list(self.prompts_dir.glob("*.txt")))
        return [f.stem for f in prompt_files]
    
    def get_processed_prompts(self):
        """Get list of already processed prompts"""
        if not os.path.exists(self.progress_file):
            return []
        
        with open(self.progress_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    
    def get_next_unprocessed_prompt(self):
        """Get the next unprocessed prompt"""
        all_prompts = self.get_all_prompts()
        processed_prompts = self.get_processed_prompts()
        
        # Find first unprocessed prompt
        for prompt_name in all_prompts:
            if prompt_name not in processed_prompts:
                # Read the prompt content
                prompt_file = self.prompts_dir / f"{prompt_name}.txt"
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_content = f.read().strip()
                
                return prompt_name, prompt_content
        
        return None, None  # All prompts processed
    
    def mark_as_processed(self, prompt_name):
        """Mark a prompt as processed"""
        processed = self.get_processed_prompts()
        processed.append(prompt_name)
        
        with open(self.progress_file, 'w') as f:
            for p in processed:
                f.write(f"{p}\n")
        
        logger.info(f"✅ Marked '{prompt_name}' as processed")
    
    def get_status(self):
        """Get current processing status"""
        all_prompts = self.get_all_prompts()
        processed_prompts = self.get_processed_prompts()
        next_prompt, _ = self.get_next_unprocessed_prompt()
        
        return {
            "total_prompts": len(all_prompts),
            "processed": len(processed_prompts),
            "remaining": len(all_prompts) - len(processed_prompts),
            "next_prompt": next_prompt,
            "processed_list": processed_prompts
        }
    
    def reset_progress(self):
        """Reset progress (start over)"""
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        logger.info("🔄 Progress reset - starting fresh")
    
    def generate_single_video(self):
        """Generate one video for the next unprocessed prompt"""
        try:
            # Get next unprocessed prompt
            prompt_name, prompt_content = self.get_next_unprocessed_prompt()
            
            if prompt_name is None:
                logger.info("🎉 All prompts have been processed!")
                return None
            
            logger.info(f"📝 Processing: {prompt_name}")
            logger.info(f"📖 Prompt: {prompt_content[:100]}...")
            
            # Run the pipeline
            from .bedtime_history_pipeline import BedtimeHistoryPipeline
            pipeline = BedtimeHistoryPipeline()
            result = pipeline.run(prompt_content)
            
            if result and result.get('success'):
                logger.info(f"✅ Video generated successfully!")
                logger.info(f"📁 File: {result.get('video_file', 'Unknown')}")
                
                # Mark as processed
                self.mark_as_processed(prompt_name)
                
                # Get updated status
                status = self.get_status()
                logger.info(f"📊 Progress: {status['processed']}/{status['total_prompts']} completed")
                
                return {
                    'prompt_name': prompt_name,
                    'video_file': result.get('video_file'),
                    'video_result': result,
                    'status': status
                }
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Pipeline returned None'
                logger.error(f"❌ Video generation failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating video: {e}")
            return None 