# video2mp4

Convert videos to MP4 by extending a single frame to match the audio length. This is useful when the video stream is damaged, has very low frame count, or has timing metadata that social platforms misread.

## The Problem

Some video players and platforms (like **Instagram**, TikTok, and other social media apps) determine playable length from frames instead of audio duration. When a file has:

- **10 frames** at 0.45 FPS = about **22 seconds of video stream**
- **22 seconds of audio**

Platforms may still calculate duration as `10 frames / 30 fps = 0.33 seconds`.

**Result:** a multi-second clip can appear as less than one second and audio gets cut off.

### Why This Happens

- Screen recordings can have very few keyframes
- Variable frame rate (VFR) metadata can confuse parsers
- Corrupted/misaligned timestamps can break frame decode
- Audio/video track durations can disagree in some containers

## The Solution

`video2mp4` rebuilds the video stream using one decodable frame and the original audio duration:

1. Read the true audio duration.
2. Recover a usable frame from the source video.
3. Extend that frame to full audio length.
4. Export a standard MP4 stream at target FPS.

If frame recovery fails, it can use a custom fallback image or a generated black frame.

## Features

- **Single-Frame Rebuild**: Creates a valid MP4 stream from one frame + original audio
- **Audio-Preserving**: Keeps original audio timing/content
- **Multi-Step Frame Recovery**:
  - MoviePy frame probes across candidate timestamps
  - OpenCV fallback read
  - ffmpeg single-frame extraction
  - ffmpeg remux with `+genpts` and retry
- **Fallback Poster Support**: `--fallback-image` when no source frame is decodable
- **Batch Conversion**: Convert all supported videos in a folder
- **Format Support**: `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`
- **CLI + Python API**

## Installation

### From Source

```bash
cd video2mp4
pip install -e .
# or:
pip install .
```

### Dependencies

Required:

- Python 3.9+
- `moviepy>=2.0.0`
- FFmpeg (installed on system or resolvable via `imageio-ffmpeg`)

Optional helpers used automatically if installed:

- `opencv-python` for frame extraction fallback
- `Pillow` for `--fallback-image` loading/resizing
- `imageio-ffmpeg` for ffmpeg binary resolution

Install FFmpeg:

- Windows: `winget install ffmpeg` or https://ffmpeg.org/
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg` (or distro equivalent)

## CLI Usage

### Convert a Single File

```bash
# Writes input_converted_mov.mp4 next to input.mov
video2mp4 input.mov

# Custom output path
video2mp4 input.mov -o output.mp4

# Custom FPS
video2mp4 input.mov --fps 60

# Use poster if frame decode fails
video2mp4 input.mov --fallback-image poster.png
```

### Batch Convert a Folder

```bash
# Writes files to ./videos/output/
video2mp4 ./videos --batch

# Custom output folder
video2mp4 ./videos --batch -o ./converted

# Custom extensions
video2mp4 ./videos --batch -e ".mov,.mp4"

# Poster fallback for entire batch
video2mp4 ./videos --batch --fallback-image poster.png
```

### All CLI Options

```text
usage: video2mp4 [-h] [-o OUTPUT] [-b] [--fps FPS] [--codec CODEC]
                 [--audio-codec AUDIO_CODEC]
                 [--fallback-image FALLBACK_IMAGE]
                 [-e EXTENSIONS] [-v] [-q]
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
  --fallback-image FALLBACK_IMAGE
                        Optional image used if a video frame cannot be decoded
  -e, --extensions      Comma-separated list of extensions
                        (default: .mp4,.mov,.avi,.mkv,.wmv,.flv,.webm)
  -v, --version         Show version number and exit
  -q, --quiet           Suppress progress output
```

## Python API

### Convert a Single Video

```python
from video2mp4 import convert_video

output_path = convert_video(
    "input.mov",
    output_path="output.mp4",
    fps=30,
    codec="libx264",
    audio_codec="aac",
    frame_index=0,
    fallback_image="poster.png",
    on_progress=print,
)

print(f"Saved to: {output_path}")
```

### Batch Convert Videos

```python
from video2mp4 import convert_videos_in_folder

results = convert_videos_in_folder(
    "./videos",
    output_folder="./converted",
    extensions={".mov", ".mp4"},
    fps=30,
    codec="libx264",
    audio_codec="aac",
    fallback_image="poster.png",
    on_progress=print,
)

print(f"Converted {len(results)} videos")
for path in results:
    print(path)
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
    fallback_image: str | Path | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> Path
```

Parameters:

- `input_path`: Input video path
- `output_path`: Output file path (default: `{stem}_converted_{orig_ext}.mp4`)
- `fps`: Output frames per second
- `codec`: Video codec
- `audio_codec`: Audio codec
- `frame_index`: Preferred frame index to probe first
- `fallback_image`: Optional image path used if no frame is decodable
- `on_progress`: Optional progress callback

Raises:

- `FileNotFoundError`: Input does not exist
- `ValueError`: Audio track missing/unreadable

#### `convert_videos_in_folder()`

```python
convert_videos_in_folder(
    input_folder: str | Path,
    output_folder: str | Path | None = None,
    extensions: set | None = None,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
    fallback_image: str | Path | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[Path]
```

Parameters:

- `input_folder`: Folder containing videos
- `output_folder`: Output folder (default: `{input_folder}/output`)
- `extensions`: Set of file extensions to include
- `fps`: Output frames per second
- `codec`: Video codec
- `audio_codec`: Audio codec
- `fallback_image`: Optional image path used when frame recovery fails
- `on_progress`: Optional progress callback

Returns:

- List of converted output paths

## Examples

### Fix Corrupted Video With Audio Intact

```bash
video2mp4 corrupted_video.mov -o fixed_video.mp4
```

### Batch Process Screen Recordings

```bash
video2mp4 ./recordings --batch -o ./processed -e ".mov,.mp4"
```

### Force Poster Fallback

```bash
video2mp4 broken.mp4 --fallback-image poster.png
```

## How It Works

1. Load audio and measure true duration.
2. Try decoding a frame from the video stream.
3. Retry with fallback decoders/remux if needed.
4. Choose recovered frame, fallback image, or black placeholder.
5. Build constant-frame video clip for full audio duration.
6. Attach original audio and export MP4.

## License

MIT License. See `LICENSE`.
