#!/usr/bin/env python3
"""
Extract narration text from bedtime story JSON file and save to separate files by segment.
"""

import json
import os
from pathlib import Path

def extract_narration(json_file_path):
    """Extract narration text from each segment and save to separate files."""
    
    # Create output directory
    output_dir = Path(json_file_path).parent / "narration_text"
    output_dir.mkdir(exist_ok=True)
    
    # Load the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        story_data = json.load(f)
    
    # Get the video title for naming files
    video_title = story_data.get('video_title', 'Bedtime_Story').replace(' ', '_')
    
    # Extract segments
    segments = story_data.get('segments', [])
    
    print(f"Found {len(segments)} segments in the story.")
    
    # Process each segment
    for segment in segments:
        segment_number = segment.get('segment_number', 0)
        scenes = segment.get('scenes', [])
        
        # Combine all narration text from this segment
        narration_text = ""
        for scene in scenes:
            narration_text += scene.get('narration_text', '') + "\n\n"
        
        # Save to file
        output_file = output_dir / f"{video_title}_segment_{segment_number}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(narration_text)
        
        print(f"Saved segment {segment_number} narration to {output_file}")
    
    print(f"Extraction complete. Files saved to {output_dir}")

if __name__ == "__main__":
    # Get the most recent JSON file in the OUTPUT directory
    output_dir = Path("OUTPUT")
    prompt_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    
    if not prompt_dirs:
        print("No prompt directories found in OUTPUT folder.")
        exit(1)
    
    # Get the most recent prompt directory
    latest_prompt_dir = max(prompt_dirs, key=lambda x: x.stat().st_mtime)
    
    # Find story JSON files in this directory
    story_files = list(latest_prompt_dir.glob("bedtime_story_*.json"))
    
    if not story_files:
        print(f"No story JSON files found in {latest_prompt_dir}.")
        exit(1)
    
    # Get the most recent story file
    latest_story_file = max(story_files, key=lambda x: x.stat().st_mtime)
    
    print(f"Processing story file: {latest_story_file}")
    extract_narration(latest_story_file) 