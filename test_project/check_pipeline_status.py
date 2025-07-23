#!/usr/bin/env python3
"""
Check the status of the modified pipeline that uses prompts folder.
"""

import sys
from pathlib import Path

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

def main():
    """Check current status"""
    print("📊 Pipeline Status")
    print("=" * 30)
    
    status = get_status()
    
    print(f"📈 Total prompts: {status['total_prompts']}")
    print(f"✅ Processed: {status['processed']}")
    print(f"⏳ Remaining: {status['remaining']}")
    
    if status['next_prompt']:
        print(f"🎬 Next prompt: {status['next_prompt']}")
    else:
        print("🎉 All prompts completed!")
    
    if status['processed_list']:
        print(f"📝 Processed prompts: {', '.join(status['processed_list'])}")
    
    # Calculate percentage
    if status['total_prompts'] > 0:
        percentage = (status['processed'] / status['total_prompts']) * 100
        print(f"📊 Progress: {percentage:.1f}%")
    
    print()
    print("💡 To generate next video, run: python3 test_pipeline.py")
    print("💡 To reset progress, delete: prompt_progress.txt")

if __name__ == "__main__":
    main() 