# Bedtime History Video Pipeline

This project generates calming, bedtime history videos from a single prompt. It uses Google Gemini for story and image generation, Kokoro TTS for audio, and Whisper for subtitles. The pipeline is optimized for batch processing and parallel API calls.

## Features
- Generate a multi-scene bedtime story from a prompt
- Create bedtime-optimized images for each scene
- Generate soothing narration audio using TTS
- Generate subtitles using Whisper
- Combine everything into a synchronized video
- Automatically upload videos to YouTube

---

## Input & Output Summary

| **Input** | **Description** |
|-----------|----------------|
| Prompt    | `.txt` file in `prompts/` (one topic or story idea per file) |

| **Output** | **Description** |
|------------|----------------|
| Video      | `bedtime_video_<timestamp>.mp4` in `OUTPUT/` |
| Story JSON | Full story structure and metadata |
| Images     | Scene images (PNG) |
| Audio      | Scene and combined narration (WAV) |
| Subtitles  | SRT file for video |
| YouTube URL| If uploaded, the video link |
| Metadata   | Pipeline run details (JSON) |

---

## Step-by-Step Guide

### 1. **Clone the Repository & Prepare Environment**
- Clone this repository to your local machine.
- (Optional but recommended) Create and activate a Python virtual environment:
  ```bash
  python3 -m venv bedtime_env
  source bedtime_env/bin/activate
  ```

### 2. **Install Dependencies**
- Install all required Python packages:
  ```bash
  pip install -r requirements.txt
  ```

### 3. **Install FFmpeg and FFprobe (Required for Video/Audio Processing)**
- The pipeline requires FFmpeg and FFprobe binaries.
- **Windows:**
  1. Download FFmpeg from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) (choose the Windows build).
  2. Extract and place `ffmpeg.exe` and `ffprobe.exe` in the `ffmpeg/` directory at the project root **OR** add the FFmpeg `bin/` directory to your system PATH.
- **macOS/Linux:**
  - Install via Homebrew: `brew install ffmpeg`
  - Or use your package manager (e.g., `apt install ffmpeg`)
- The pipeline will automatically use the correct binary for your OS.

### 4. **Prepare TTS Models**
- Download the Kokoro ONNX model and voices files.
- Place them in the `kokoro/` directory as specified in `src/config.py`:
  - `kokoro-v1.0.onnx`
  - `voices-v1.0.bin`

### 5. **Configure API Keys**
- The project uses multiple Google Gemini API keys for parallel image and story generation.
- Add your API keys to the `GEMINI_API_KEYS` list in `src/config.py`.

### 6. **Set Up YouTube API (New)**
- Create a project in the Google Cloud Console
- Enable the YouTube Data API v3
- Create OAuth 2.0 credentials (Desktop app type)
- Download the client secrets JSON file
- Place the file in the project root directory as `client_secrets.json`
- Configure YouTube settings in `src/config.py` if needed:
  - `default_privacy`: "private", "unlisted", or "public"
  - `default_category`: YouTube category ID (22 = "People & Blogs", 27 = "Education")
  - `notify_subscribers`: Whether to notify subscribers
  - `auto_upload`: Enable/disable automatic uploads

### 7. **Add Your Prompts**
- Place your prompts as individual `.txt` files in the `prompts/` directory.
- Each file should contain a single prompt (one topic or story idea per file).
- Example:
  - `prompts/ancient_egypt.txt`
  - `prompts/library_alexandria.txt`

### 8. **How Progress Tracking Works**
- The pipeline keeps track of which prompts have been processed using the `prompt_progress.txt` file.
- Each time a prompt is successfully processed, its filename (without `.txt`) is added as a new line to this file.
- On each run, the pipeline:
  1. Reads all prompt filenames in `prompts/`.
  2. Reads the list of processed prompt names from `prompt_progress.txt`.
  3. Finds the first prompt in `prompts/` that is **not** in `prompt_progress.txt` and processes it.
  4. After successful processing, appends that prompt name to `prompt_progress.txt`.
- If all prompts are processed, the pipeline will log that all prompts have been completed.
- To reset progress, simply delete the `prompt_progress.txt` file.

### 9. **Run the Pipeline**
- From the `test_project` directory, run:
  ```bash
  python3 test_pipeline.py
  ```
- The script will:
  1. **Test all components** (story, image, audio, subtitle, video creation)
  2. **Generate the full bedtime story** from the next unprocessed prompt
  3. **Create images** for each scene using Gemini (parallelized)
  4. **Generate narration audio** for each scene using Kokoro TTS
  5. **Combine audio** into a single file
  6. **Generate subtitles** using Whisper
  7. **Create the final video** with images, audio, and subtitles
  8. **Upload the video to YouTube** with appropriate metadata
  9. **Save all outputs** in the `OUTPUT/` directory
  10. **Mark the prompt as processed** in `prompt_progress.txt`

### 10. **Find Your Video**
- The final video will be saved in `OUTPUT/` as `bedtime_video_<timestamp>.mp4`.
- If YouTube upload was successful, the video URL will be displayed in the console and saved in the pipeline metadata.
- Other outputs (story JSON, images, audio, subtitles, metadata) are also saved in `OUTPUT/`.

### 11. **(Optional) Test YouTube Upload**
- To test just the YouTube API connection:
  ```bash
  python3 test_youtube_upload.py --test-connection
  ```
- To test uploading a specific video:
  ```bash
  python3 test_youtube_upload.py --upload --video-file="OUTPUT/prompt_1/bedtime_video_20250718_223235.mp4" --title="My Test Video"
  ```
- To test the full pipeline integration:
  ```bash
  python3 test_youtube_integration.py --test-pipeline
  ```

### 12. **(Optional) Monitor Progress**
- Use `watch_progress.py` to monitor the number of images and videos generated in real time:
  ```bash
  python3 watch_progress.py
  ```

### 13. **(Optional) Debug or Test Individual Components**
- Use the provided test scripts (e.g., `test_parallel_images.py`, `test_video_creation.py`) to debug or validate specific parts of the pipeline.

---

## Cross-Platform Support
- This pipeline is tested on both **Windows** and **macOS**.
- All file paths are handled using Python's `pathlib` for compatibility.
- If you encounter issues on Windows (e.g., missing DLLs, FFmpeg not found), ensure FFmpeg/FFprobe are in the correct location or added to your PATH.

## Notes
- The pipeline uses multiple Gemini API keys for parallel image generation (see `src/config.py`).
- All configuration (models, API keys, settings) is in `src/config.py`.
- The pipeline now processes prompts sequentially from the `prompts/` folder and tracks progress in `prompt_progress.txt`.
- For best results, use a detailed, calming prompt in each `.txt` file in `prompts/`.
- To reset progress, delete the `prompt_progress.txt` file.
- The first time you run YouTube upload, it will open a browser window for authentication.
- After authenticating once, credentials are saved to `youtube_token.pickle` for future use.

## Troubleshooting
- **FFmpeg not found:** Make sure `ffmpeg.exe` and `ffprobe.exe` are in the `ffmpeg/` directory or your system PATH (Windows), or installed via your package manager (macOS/Linux).
- **YouTube upload/auth issues:** The first upload will open a browser for authentication. If it fails, delete `youtube_token.pickle` and try again.
- **Audio/Video errors:** Check that all dependencies are installed and that your prompt files are correctly formatted.

## License
This project is for educational and non-commercial use only. 