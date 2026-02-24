"""Core video conversion functionality."""

from pathlib import Path
from typing import Any, Callable, Optional, Union
import os
import subprocess
import tempfile
import numpy as np
from moviepy import AudioFileClip, ImageClip, VideoFileClip


def _iter_candidate_timestamps(video: VideoFileClip, frame_index: int) -> list[float]:
    """Build a small ordered set of timestamps to probe for a decodable frame."""
    duration = float(video.duration or 0.0)
    fps = float(video.fps or 0.0)

    candidates: list[float] = []

    if fps > 0:
        frame_candidates = [frame_index, 0, 1, 2, 5, 10]
        if duration > 0:
            max_frame = max(int(duration * fps) - 1, 0)
            frame_candidates.extend([max_frame // 10, max_frame // 4, max_frame // 2, max_frame])

        for idx in frame_candidates:
            if idx < 0:
                continue
            candidates.append(idx / fps)

    time_candidates = [0.0, 0.1, 0.25, 0.5, 1.0]
    if duration > 0:
        time_candidates.extend([duration * 0.25, duration * 0.5, max(duration - 0.2, 0.0)])
    candidates.extend(time_candidates)

    # Clamp and preserve order while removing near-duplicates.
    unique: list[float] = []
    max_time = duration
    epsilon = 1.0 / fps if fps > 0 else 0.001
    upper_bound = max(max_time - epsilon, 0.0)

    for ts in candidates:
        clamped = min(max(float(ts), 0.0), upper_bound)
        if any(abs(clamped - seen) < 0.001 for seen in unique):
            continue
        unique.append(clamped)

    return unique


def _get_fallback_frame_opencv(input_path: Path) -> Optional[Any]:
    """Try OpenCV to read the first decodable frame if MoviePy frame reads fail."""
    try:
        import cv2
    except Exception:
        return None

    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        return None

    try:
        for _ in range(300):
            ok, frame = capture.read()
            if not ok or frame is None or frame.size == 0:
                continue

            # OpenCV returns BGR; MoviePy expects RGB arrays.
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    finally:
        capture.release()

    return None


def _extract_decodable_frame(
    video: VideoFileClip,
    input_path: Path,
    frame_index: int,
    on_progress: Optional[Callable[[str], None]] = None,
) -> Any:
    """Extract a decodable frame using MoviePy probes, then OpenCV fallback."""
    last_error: Optional[Exception] = None

    for ts in _iter_candidate_timestamps(video, frame_index):
        try:
            frame = video.get_frame(ts)
            if frame is not None:
                return frame
        except Exception as exc:
            last_error = exc

    fallback_frame = _get_fallback_frame_opencv(input_path)
    if fallback_frame is not None:
        if on_progress:
            on_progress("MoviePy frame probe failed, using OpenCV fallback frame")
        return fallback_frame

    if last_error is not None:
        raise last_error
    raise ValueError(f"Unable to decode any frame from {input_path.name}")


def _probe_video_dimensions(input_path: Path) -> tuple[int, int]:
    """Best-effort probe of input video width/height."""
    width = 0
    height = 0

    try:
        import cv2
    except Exception:
        cv2 = None

    if cv2 is not None:
        capture = cv2.VideoCapture(str(input_path))
        try:
            if capture.isOpened():
                width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        finally:
            capture.release()

    if width <= 0 or height <= 0:
        return (720, 1280)
    return (width, height)


def _create_placeholder_frame(input_path: Path) -> Any:
    """Create a black frame used when no decodable source frame exists."""
    width, height = _probe_video_dimensions(input_path)
    return np.zeros((height, width, 3), dtype=np.uint8)


def _load_image_frame(image_path: Union[str, Path], target_size: tuple[int, int]) -> Any:
    """Load fallback image and resize to the target frame size."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Fallback image not found: {image_path}")

    try:
        from PIL import Image
    except Exception as exc:
        raise ValueError("Pillow is required to load fallback images") from exc

    image = Image.open(str(image_path)).convert("RGB")
    target_width, target_height = target_size
    if image.size != (target_width, target_height):
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return np.array(image, dtype=np.uint8)


def _get_ffmpeg_binary() -> str:
    """Resolve ffmpeg executable path."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _extract_first_frame_ffmpeg(input_path: Path) -> Optional[Any]:
    """Extract first decodable frame with ffmpeg into an RGB numpy array."""
    ffmpeg_bin = _get_ffmpeg_binary()

    try:
        from PIL import Image
    except Exception:
        return None

    fd, output_png = tempfile.mkstemp(suffix=".png")
    os.close(fd)

    try:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-frames:v",
            "1",
            output_png,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            return None

        if not Path(output_png).exists() or Path(output_png).stat().st_size == 0:
            return None

        image = Image.open(output_png).convert("RGB")
        return np.array(image, dtype=np.uint8)
    except Exception:
        return None
    finally:
        try:
            os.remove(output_png)
        except OSError:
            pass


def _remux_with_genpts(input_path: Path) -> Optional[Path]:
    """Remux MP4 to regenerate timestamps for better decoder compatibility."""
    ffmpeg_bin = _get_ffmpeg_binary()

    fd, remux_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    remux_path = Path(remux_path)

    try:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "+genpts",
            "-i",
            str(input_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(remux_path),
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0 or not remux_path.exists() or remux_path.stat().st_size == 0:
            remux_path.unlink(missing_ok=True)
            return None
        return remux_path
    except Exception:
        remux_path.unlink(missing_ok=True)
        return None


def _load_audio_clip(input_path: Path) -> tuple[AudioFileClip, float]:
    """Load audio track and return audio clip with duration."""
    try:
        audio_clip = AudioFileClip(str(input_path))
    except Exception as exc:
        raise ValueError(f"No audio track found in {input_path.name}") from exc

    duration = float(audio_clip.duration or 0.0)
    if duration <= 0:
        audio_clip.close()
        raise ValueError(f"No audio track found in {input_path.name}")

    return audio_clip, duration


def _load_video_frame(
    input_path: Path,
    frame_index: int,
    on_progress: Optional[Callable[[str], None]] = None,
) -> Optional[Any]:
    """Try to decode a frame from the source video stream."""
    try:
        video = VideoFileClip(str(input_path), audio=False, decode_file=True)
    except Exception:
        if on_progress:
            on_progress("Video stream decode failed, using placeholder frame")
    else:
        try:
            return _extract_decodable_frame(video, input_path, frame_index, on_progress)
        except Exception:
            if on_progress:
                on_progress("Frame extraction failed, trying ffmpeg extraction")
        finally:
            video.close()

    # Direct ffmpeg frame extraction.
    ffmpeg_frame = _extract_first_frame_ffmpeg(input_path)
    if ffmpeg_frame is not None:
        if on_progress:
            on_progress("Recovered frame using ffmpeg extraction")
        return ffmpeg_frame

    # Final attempt: remux with regenerated timestamps, then extract first frame.
    remux_path = _remux_with_genpts(input_path)
    if remux_path is not None:
        try:
            ffmpeg_frame = _extract_first_frame_ffmpeg(remux_path)
            if ffmpeg_frame is not None:
                if on_progress:
                    on_progress("Recovered frame after ffmpeg remux")
                return ffmpeg_frame
        finally:
            remux_path.unlink(missing_ok=True)

    if on_progress:
        on_progress("Frame recovery failed, using placeholder frame")
    return None


def convert_video(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
    frame_index: int = 0,
    fallback_image: Optional[Union[str, Path]] = None,
    on_progress: Optional[Callable[[str], None]] = None
) -> Path:
    """
    Convert a video file to MP4 by extending a single frame to match audio length.
    
    Args:
        input_path: Path to the input video file
        output_path: Path for output file. If None, creates in same directory with _converted.mp4 suffix
        fps: Frames per second for output video (default: 30)
        codec: Video codec (default: libx264)
        audio_codec: Audio codec (default: aac)
        frame_index: Which frame to use (default: 0 = first frame)
        fallback_image: Optional path to image used if no video frame is decodable
        on_progress: Optional callback function for progress messages
        
    Returns:
        Path to the output file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If video has no audio track
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Generate output path if not provided
    if output_path is None:
        orig_ext = input_path.suffix.lower().replace('.', '')
        output_path = input_path.parent / f"{input_path.stem}_converted_{orig_ext}.mp4"
    else:
        output_path = Path(output_path)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(msg: str):
        if on_progress:
            on_progress(msg)
    
    log(f"Loading: {input_path.name}")
    
    audio_clip, audio_duration = _load_audio_clip(input_path)
    log(f"Audio duration: {audio_duration:.2f} seconds")

    image_clip: Optional[ImageClip] = None
    try:
        frame = _load_video_frame(input_path, frame_index, on_progress)
        if frame is None:
            if fallback_image is not None:
                target_size = _probe_video_dimensions(input_path)
                frame = _load_image_frame(fallback_image, target_size)
                log(f"Using fallback image: {Path(fallback_image).name}")
            else:
                frame = _create_placeholder_frame(input_path)
                log("Using black placeholder frame to rebuild video stream")

        # Create image clip from frame
        image_clip = ImageClip(frame).with_duration(audio_duration)

        # Add audio
        image_clip = image_clip.with_audio(audio_clip)

        # Set fps
        image_clip = image_clip.with_fps(fps)

        # Write output
        log(f"Creating {audio_duration:.2f} second video...")
        image_clip.write_videofile(
            str(output_path),
            codec=codec,
            audio_codec=audio_codec
        )

        log(f"Saved: {output_path.name}")
        return output_path
    finally:
        if image_clip is not None:
            image_clip.close()
        audio_clip.close()


def convert_videos_in_folder(
    input_folder: Union[str, Path],
    output_folder: Optional[Union[str, Path]] = None,
    extensions: Optional[set] = None,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
    fallback_image: Optional[Union[str, Path]] = None,
    on_progress: Optional[Callable[[str], None]] = None
) -> list[Path]:
    """
    Convert all videos in a folder.
    
    Args:
        input_folder: Path to folder containing input videos
        output_folder: Path for output folder. If None, creates 'output' subfolder
        extensions: Set of file extensions to process (default: {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'})
        fps: Frames per second for output videos
        codec: Video codec
        audio_codec: Audio codec
        fallback_image: Optional path to image used when a frame cannot be decoded
        on_progress: Optional callback function for progress messages
        
    Returns:
        List of paths to converted files
    """
    input_folder = Path(input_folder)
    
    if not input_folder.exists():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    
    if output_folder is None:
        output_folder = input_folder / "output"
    else:
        output_folder = Path(output_folder)
    
    output_folder.mkdir(parents=True, exist_ok=True)
    
    if extensions is None:
        extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
    
    def log(msg: str):
        if on_progress:
            on_progress(msg)
    
    converted = []
    files = [f for f in input_folder.iterdir() if f.is_file() and f.suffix.lower() in extensions]
    
    for i, file_path in enumerate(files, 1):
        log(f"\n[{i}/{len(files)}] Processing: {file_path.name}")
        
        orig_ext = file_path.suffix.lower().replace('.', '')
        output_name = f"{file_path.stem}_converted_{orig_ext}.mp4"
        output_path = output_folder / output_name
        
        try:
            result = convert_video(
                file_path,
                output_path,
                fps=fps,
                codec=codec,
                audio_codec=audio_codec,
                fallback_image=fallback_image,
                on_progress=on_progress
            )
            converted.append(result)
        except Exception as e:
            log(f"Error: {e}")
    
    return converted
