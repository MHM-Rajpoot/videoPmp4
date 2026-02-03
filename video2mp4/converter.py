"""Core video conversion functionality."""

import os
from pathlib import Path
from typing import Optional, Union, Callable
from moviepy import VideoFileClip, ImageClip


def convert_video(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
    frame_index: int = 0,
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
    
    # Load the video
    video = VideoFileClip(str(input_path))
    
    try:
        # Get audio duration
        if video.audio is not None:
            audio_duration = video.audio.duration
            log(f"Audio duration: {audio_duration:.2f} seconds")
        else:
            raise ValueError(f"No audio track found in {input_path.name}")
        
        # Get the specified frame
        frame = video.get_frame(frame_index / video.fps if video.fps else 0)
        
        # Create image clip from frame
        image_clip = ImageClip(frame).with_duration(audio_duration)
        
        # Add audio
        image_clip = image_clip.with_audio(video.audio)
        
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
        
        # Cleanup
        image_clip.close()
        
        return output_path
        
    finally:
        video.close()


def convert_videos_in_folder(
    input_folder: Union[str, Path],
    output_folder: Optional[Union[str, Path]] = None,
    extensions: Optional[set] = None,
    fps: int = 30,
    codec: str = "libx264",
    audio_codec: str = "aac",
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
                on_progress=on_progress
            )
            converted.append(result)
        except Exception as e:
            log(f"Error: {e}")
    
    return converted
