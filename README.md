# video2mp4

Convert videos to MP4 by extending a single frame to match the audio length. Perfect for fixing videos where the video track is corrupted or has fewer frames than the audio duration.

## The Problem

Some video players and platforms (like **Instagram**, TikTok, and other social media apps) determine video duration by counting frames rather than reading audio length. When a video has:

- **10 frames** at 0.45 FPS = **22 seconds of video**
- **22 seconds of audio**

These platforms see only the frame count and calculate: `10 frames ÷ 30 fps = 0.33 seconds`

**Result:** Your 22-second video gets trimmed to less than 1 second, cutting off most of the audio!

### Why This Happens

- Screen recordings or corrupted exports sometimes have very few keyframes
- Variable frame rate (VFR) videos confuse frame counters
- Some encoders prioritize audio over video frames
- MOV/MP4 containers may have mismatched track durations

### The Solution

**video2mp4** fixes this by:

1. Reading the actual audio duration (the true length)
2. Taking a single frame from the video
3. Extending that frame to match the full audio length
4. Creating a proper 30 FPS video stream

**Benefits:**
- ✅ Video duration now matches audio duration
- ✅ Platforms correctly detect the full length
- ✅ Minimal file size increase (single frame repeated, highly compressible)
- ✅ Original audio preserved perfectly
- ✅ Compatible with all social media platforms

## Features

- **Single Frame Extension**: Uses one frame from the video and extends it to match the full audio duration
- **Preserves Audio**: Keeps the original audio track intact
- **Batch Processing**: Convert entire folders of videos at once
- **Multiple Formats**: Supports MP4, MOV, AVI, MKV, WMV, FLV, WebM
- **Customizable**: Adjust FPS, codecs, and output settings
- **CLI & Python API**: Use from command line or import as a module

## Installation

### From Source

```bash
# Clone or download the repository
cd video2mp4

# Install in development mode
pip install -e .

# Or install directly
pip install .
```

### Dependencies

- Python 3.9+
- moviepy >= 2.0.0
- FFmpeg (required by moviepy)

Install FFmpeg:
- **Windows**: `winget install ffmpeg` or download from https://ffmpeg.org/
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` or equivalent

## CLI Usage

### Convert a Single File

```bash
# Basic usage - creates input_converted_mov.mp4 in same directory
video2mp4 input.mov

# Specify output file
video2mp4 input.mov -o output.mp4

# Custom FPS
video2mp4 input.mov --fps 60
```

### Batch Convert a Folder

```bash
# Convert all videos in a folder (output to ./videos/output/)
video2mp4 ./videos --batch

# Specify output folder
video2mp4 ./videos --batch -o ./converted

# Only convert specific extensions
video2mp4 ./videos --batch -e ".mov,.mp4"
```

### All CLI Options

```
usage: video2mp4 [-h] [-o OUTPUT] [-b] [--fps FPS] [--codec CODEC]
                 [--audio-codec AUDIO_CODEC] [-e EXTENSIONS] [-v] [-q]
                 input

positional arguments:
  input                 Input video file or folder (with --batch)

options:
  -h, --help            Show help message and exit
  -o, --output OUTPUT   Output file path or folder (with --batch)
  -b, --batch           Process all videos in input folder
  --fps FPS             Output frames per second (default: 30)
  --codec CODEC         Video codec (default: libx264)
  --audio-codec AUDIO_CODEC
                        Audio codec (default: aac)
  -e, --extensions      Comma-separated list of extensions (default: .mp4,.mov,.avi,.mkv,.wmv,.flv,.webm)
  -v, --version         Show version number and exit
  -q, --quiet           Suppress progress output
```

## Python API

### Convert a Single Video

```python
from video2mp4 import convert_video

# Basic usage
output_path = convert_video("input.mov")
print(f"Saved to: {output_path}")

# With options
output_path = convert_video(
    "input.mov",
    output_path="output.mp4",
    fps=60,
    codec="libx264",
    audio_codec="aac",
    on_progress=print  # Print progress messages
)
```

### Batch Convert Videos

```python
from video2mp4 import convert_videos_in_folder

# Convert all videos in a folder
results = convert_videos_in_folder(
    "./videos",
    output_folder="./converted",
    extensions={".mov", ".mp4"},
    fps=30,
    on_progress=print
)

print(f"Converted {len(results)} videos")
for path in results:
    print(f"  - {path}")
```

### Function Reference

#### `convert_video()`

```python
convert_video(
    input_path: str | Path,
    output_path: str | Path | None = None,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
    frame_index: int = 0,
    on_progress: Callable[[str], None] | None = None
) -> Path
```

**Parameters:**
- `input_path`: Path to the input video file
- `output_path`: Output file path. If None, creates `{name}_converted_{ext}.mp4`
- `fps`: Output frames per second (default: 30)
- `codec`: Video codec (default: libx264)
- `audio_codec`: Audio codec (default: aac)
- `frame_index`: Which frame to use (default: 0 = first frame)
- `on_progress`: Callback function for progress messages

**Returns:** Path to the output file

**Raises:**
- `FileNotFoundError`: If input file doesn't exist
- `ValueError`: If video has no audio track

#### `convert_videos_in_folder()`

```python
convert_videos_in_folder(
    input_folder: str | Path,
    output_folder: str | Path | None = None,
    extensions: set | None = None,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
    on_progress: Callable[[str], None] | None = None
) -> list[Path]
```

**Parameters:**
- `input_folder`: Path to folder containing input videos
- `output_folder`: Output folder path. If None, creates `output` subfolder
- `extensions`: Set of file extensions to process (default: common video extensions)
- `fps`: Output frames per second
- `codec`: Video codec
- `audio_codec`: Audio codec
- `on_progress`: Callback function for progress messages

**Returns:** List of paths to converted files

## Examples

### Fix Corrupted Video Files

```bash
# Videos with missing frames but intact audio
video2mp4 corrupted_video.mov -o fixed_video.mp4
```

### Create Still Image Videos from Audio

```bash
# Use first frame as a still image for the entire audio duration
video2mp4 presentation.mov --fps 1
```

### Batch Process Screen Recordings

```bash
# Convert all screen recordings
video2mp4 ./recordings --batch -o ./processed -e ".mov"
```

## How It Works

1. **Load Video**: Opens the input video file using moviepy
2. **Extract Audio**: Gets the audio track and its duration
3. **Capture Frame**: Extracts a single frame (first frame by default)
4. **Create Video**: Creates a new video with the frame extended to match audio duration
5. **Merge Audio**: Combines the extended video with the original audio
6. **Export**: Writes the final MP4 file with specified codec settings

## License

MIT License - See LICENSE file for details.
