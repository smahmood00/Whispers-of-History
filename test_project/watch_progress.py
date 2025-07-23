#!/usr/bin/env python3
"""Watch pipeline progress"""

import time
import glob
import os

def watch_progress():
    """Monitor pipeline progress"""
    print("🔍 Watching pipeline progress...")
    print("Press Ctrl+C to stop watching")
    
    last_count = 0
    
    try:
        while True:
            # Check for story files
            stories = glob.glob("OUTPUT/bedtime_story_*.json")
            
            # Check for image files  
            images = glob.glob("OUTPUT/scene_*.png")
            
            # Check for video files
            videos = glob.glob("OUTPUT/bedtime_video_*.mp4")
            
            print(f"\r🎬 Stories: {len(stories)} | 🖼️  Images: {len(images)} | 🎥 Videos: {len(videos)}", end="", flush=True)
            
            if len(images) != last_count and len(images) > 0:
                print(f"\n✨ Progress: {len(images)} images generated!")
                last_count = len(images)
                
            if len(videos) > 0:
                video_file = videos[-1]
                size_mb = os.path.getsize(video_file) / (1024*1024)
                print(f"\n🎉 VIDEO COMPLETE! {video_file} ({size_mb:.1f}MB)")
                break
                
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n👋 Stopped watching")

if __name__ == "__main__":
    watch_progress() 