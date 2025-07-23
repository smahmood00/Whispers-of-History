#!/usr/bin/env python3
"""Debug image generation with actual story scenes"""

import subprocess
import sys
from pathlib import Path

def debug_image_generation():
    """Debug why images aren't being generated"""
    
    test_code = '''
import sys
import json
from src.parallel_image_generator import ParallelBedtimeImageGenerator
from src.config import OUTPUT_DIR
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("🔍 Debugging image generation issue...")

# Load the actual story
with open("OUTPUT/bedtime_story_20250713_231148.json", "r") as f:
    story = json.load(f)

scenes = story["scenes"]
print(f"📊 Story has {len(scenes)} scenes")

# Test with just the first 2 scenes
test_scenes = scenes[:2]
print(f"🧪 Testing with first {len(test_scenes)} scenes...")

print("Scene 1 prompt:", test_scenes[0]["image_prompt"][:100] + "...")
print("Scene 2 prompt:", test_scenes[1]["image_prompt"][:100] + "...")

try:
    generator = ParallelBedtimeImageGenerator(OUTPUT_DIR)
    print(f"✅ Generator initialized with {len(generator.clients)} APIs")
    
    # Test generation
    print("🎨 Starting image generation...")
    results = generator.process(test_scenes)
    
    successful = sum(1 for r in results if r.get("success", False))
    print(f"📈 Results: {successful}/{len(test_scenes)} successful")
    
    for i, result in enumerate(results):
        if result.get("success"):
            print(f"✅ Scene {i+1}: {result.get('output_path', 'No path')}")
        else:
            print(f"❌ Scene {i+1}: {result.get('error', 'Unknown error')}")
            
    # Check if files were actually created
    import glob
    png_files = glob.glob("OUTPUT/scene_*.png")
    print(f"📁 PNG files found: {len(png_files)}")
    for f in png_files:
        print(f"  - {f}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
'''
    
    # Run the test
    result = subprocess.run([sys.executable, "-c", test_code], 
                          cwd=Path(__file__).parent, 
                          capture_output=True, 
                          text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"Exit code: {result.returncode}")
    return result.returncode == 0

if __name__ == "__main__":
    success = debug_image_generation()
    sys.exit(0 if success else 1) 