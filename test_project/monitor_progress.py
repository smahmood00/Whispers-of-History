#!/usr/bin/env python3
"""Monitor pipeline progress and show latest results"""

import json
import time
import glob
from pathlib import Path

def get_latest_story():
    """Get the most recent story file"""
    story_files = glob.glob("OUTPUT/bedtime_story_*.json")
    if not story_files:
        return None
    
    # Sort by modification time
    latest_file = max(story_files, key=lambda x: Path(x).stat().st_mtime)
    return latest_file

def analyze_story(story_file):
    """Analyze a story file and show statistics"""
    try:
        with open(story_file, 'r') as f:
            story = json.load(f)
        
        scenes = story['scenes']
        scene_count = len(scenes)
        
        # Count words
        total_words = 0
        word_counts = []
        for scene in scenes:
            words = len(scene['narration_text'].split())
            total_words += words
            word_counts.append(words)
        
        avg_words_per_scene = total_words / scene_count if scene_count > 0 else 0
        min_words = min(word_counts) if word_counts else 0
        max_words = max(word_counts) if word_counts else 0
        
        print(f"📄 Story File: {story_file}")
        print(f"📊 Statistics:")
        print(f"   Scenes: {scene_count} (target: 70+)")
        print(f"   Total words: {total_words} (target: 3000+)")
        print(f"   Average words/scene: {avg_words_per_scene:.1f}")
        print(f"   Words per scene range: {min_words}-{max_words}")
        
        # Status
        meets_scenes = scene_count >= 70
        meets_words = total_words >= 3000
        
        print(f"✅ Status:")
        print(f"   Scene target: {'✅' if meets_scenes else '❌'} ({scene_count}/70)")
        print(f"   Word target: {'✅' if meets_words else '❌'} ({total_words}/3000)")
        
        if meets_scenes and meets_words:
            print("🎉 ALL TARGETS MET! Ready for parallel image generation!")
        elif meets_words and not meets_scenes:
            print("⚠️  Word count met but need more scenes for 70+ images")
        else:
            print("⚠️  Still working towards targets...")
            
        return scene_count, total_words, meets_scenes and meets_words
        
    except Exception as e:
        print(f"❌ Error analyzing {story_file}: {e}")
        return 0, 0, False

def main():
    """Monitor progress"""
    print("🔍 Monitoring Pipeline Progress...")
    print("=" * 60)
    
    latest_story = get_latest_story()
    if latest_story:
        analyze_story(latest_story)
    else:
        print("📭 No story files found yet...")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 