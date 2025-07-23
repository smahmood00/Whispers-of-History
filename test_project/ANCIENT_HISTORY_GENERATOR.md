# Ancient History Story Generator

This document describes the implementation of the Ancient History Story Generator for the "Whispers of History" YouTube channel.

## Overview

The Ancient History Story Generator creates bedtime stories focused on ancient history topics. It uses a two-stage generation process:

1. **Generate Master Outline**: Creates a detailed outline for all chapters
2. **Generate Chapters Sequentially**: Generates each chapter with context from previous chapters

The generator produces two JSON files:
- `story_outline_TIMESTAMP.json`: The master outline
- `bedtime_story_TIMESTAMP.json`: The complete story with all chapters and scenes

## Features

- **Dynamic Chapter Calculation**: Automatically calculates chapters based on total word count
- **Consistent Scene Structure**: Each chapter has exactly 25 scenes
- **Contextual Generation**: Each chapter is generated with context from previous chapters
- **Progress Tracking**: Saves progress after each chapter
- **Pipeline Compatibility**: Output is compatible with the existing pipeline
- **Soothing Tone**: Uses specific tone and style guidelines for bedtime stories

## File Structure

```
src/
  ancient_history_story_generator.py  # Main implementation
test_ancient_history_generator.py     # Standalone test script
integrate_ancient_history_generator.py # Pipeline integration script
```

## Usage

### Standalone Testing

To test the generator independently:

```bash
python test_ancient_history_generator.py --topic "Ancient Rome" --output-dir OUTPUT/test
```

Options:
- `--topic`: The historical topic to generate a story about
- `--output-dir`: Directory to save the generated files
- `--test-only`: Run the built-in test method only

### Pipeline Integration

To integrate with the pipeline:

```bash
python integrate_ancient_history_generator.py --prompt-name prompt_1
```

Options:
- `--prompt-name`: Name of the prompt file in the prompts/ directory
- `--output-dir`: Base output directory
- `--run-full-pipeline`: Run the full pipeline including image generation, audio, etc.

## Implementation Details

### JSON Structure

#### Outline JSON
```json
{
  "story_title": "The Rise of Cyrus the Great",
  "video_title": "🌙 Ancient Persia: The Rise of Cyrus the Great | Whispers of History",
  "video_description": "Journey back to ancient Persia...",
  "thumbnail_description": "A majestic portrait of Cyrus the Great...",
  "historical_context": "6th century BCE, Ancient Persia...",
  "total_chapters": 8,
  "chapter_outlines": [
    {
      "chapter_number": 1,
      "chapter_title": "The Young Prince of Anshan",
      "historical_setting": "559 BCE, Kingdom of Anshan",
      "key_events": ["Event 1", "Event 2", "Event 3"],
      "historical_facts": ["Fact 1", "Fact 2"],
      "emotional_tone": "Contemplative, awe-inspiring"
    },
    // ... more chapter outlines
  ]
}
```

#### Story JSON
```json
{
  "video_title": "🌙 Ancient Persia: The Rise of Cyrus the Great | Whispers of History",
  "video_description": "Journey back to ancient Persia...",
  "thumbnail_description": "A majestic portrait of Cyrus the Great...",
  "total_words": 8000,
  "total_chapters": 8,
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "The Young Prince of Anshan",
      "scenes": [
        {
          "scene_number": 1,
          "narration_text": "In the shadow of towering mountains...",
          "image_prompt": "A young Persian prince in traditional robes...",
          "chapter_number": 1
        },
        // ... 25 scenes
      ]
    },
    // ... more chapters
  ],
  "scenes": [
    // Flattened list of all scenes with global scene numbers
  ]
}
```

### Tone and Style Guidelines

1. **SOOTHING NARRATIVE VOICE**
   - Speak slowly and softly, as if sharing a secret by candlelight
   - Let words flow gently, without sudden shifts
   - Use subtle pauses and a warm, intimate tone

2. **SENSORY-RICH DESCRIPTIONS**
   - Describe historical settings through the five senses
   - Use soft, calming imagery
   - Focus on gentle details that slowly unfold

3. **BALANCED HISTORICAL ACCURACY**
   - Let history gently reveal itself through feelings and small moments
   - Avoid overwhelming with names or dates
   - Anchor the story in human experiences

4. **THOUGHTFUL PACING**
   - Begin with soft, slow scene-setting
   - Allow stories to breathe and unfold at their own gentle pace
   - Introduce quiet tension or soft drama
   - End with a reflective, peaceful tone

5. **LANGUAGE CHOICES**
   - Use words that flow like a lullaby
   - Choose language that feels like a gentle melody
   - Repeat soothing phrases or motifs gently
   - Avoid harsh sounds or abrupt expressions

6. **EMOTIONAL RESONANCE**
   - Bring out quiet emotions that connect us across time
   - Introduce gentle drama through personal dilemmas
   - Focus on strategy, silence, or resolution rather than violence
   - Create a sense of sharing in a sacred moment

## Pipeline Compatibility

The generator is designed to be compatible with the existing pipeline:

1. **Image Generator**: Uses `image_prompt` field for each scene
2. **Audio Generator**: Uses `narration_text` field for each scene
3. **Video Creator**: Uses the flattened scene structure
4. **YouTube Uploader**: Uses `video_title` and `video_description` fields

## Error Handling

- **API Retry Logic**: Implements retry with backoff for API calls
- **Progress Saving**: Saves progress after each chapter
- **JSON Validation**: Validates and cleans JSON responses

## Testing

The generator includes a built-in test method that generates a story about Ancient Egypt.

To run the test:

```bash
python test_ancient_history_generator.py --test-only
``` 