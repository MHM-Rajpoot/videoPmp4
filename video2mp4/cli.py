"""Command-line interface for video2mp4."""

import argparse
import sys
from pathlib import Path
from . import __version__
from .converter import convert_video, convert_videos_in_folder


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="video2mp4",
        description="Convert videos to MP4 by extending a single frame to match audio length.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  video2mp4 input.mov                      Convert single file
  video2mp4 input.mov -o output.mp4        Convert with custom output name
  video2mp4 ./videos --batch               Convert all videos in folder
  video2mp4 ./videos --batch -o ./output   Convert to specific output folder
  video2mp4 input.mov --fps 60             Use 60 fps output
        """
    )
    
    parser.add_argument(
        "input",
        type=str,
        help="Input video file or folder (with --batch)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path or folder (with --batch)"
    )
    
    parser.add_argument(
        "-b", "--batch",
        action="store_true",
        help="Process all videos in input folder"
    )
    
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Output frames per second (default: 30)"
    )
    
    parser.add_argument(
        "--codec",
        type=str,
        default="libx264",
        help="Video codec (default: libx264)"
    )
    
    parser.add_argument(
        "--audio-codec",
        type=str,
        default="aac",
        help="Audio codec (default: aac)"
    )
    
    parser.add_argument(
        "-e", "--extensions",
        type=str,
        default=".mp4,.mov,.avi,.mkv,.wmv,.flv,.webm",
        help="Comma-separated list of extensions to process in batch mode"
    )
    
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    args = parser.parse_args()
    
    def log(msg: str):
        if not args.quiet:
            print(msg)
    
    input_path = Path(args.input)
    
    try:
        if args.batch:
            # Batch mode - process folder
            if not input_path.is_dir():
                print(f"Error: {input_path} is not a directory", file=sys.stderr)
                sys.exit(1)
            
            extensions = {f".{ext.strip().lstrip('.')}" for ext in args.extensions.split(",")}
            
            log("=" * 60)
            log("VIDEO2MP4 - Batch Conversion")
            log("=" * 60)
            log(f"Input folder: {input_path}")
            log(f"Extensions: {', '.join(extensions)}")
            
            results = convert_videos_in_folder(
                input_path,
                output_folder=args.output,
                extensions=extensions,
                fps=args.fps,
                codec=args.codec,
                audio_codec=args.audio_codec,
                on_progress=log
            )
            
            log("\n" + "=" * 60)
            log(f"Converted {len(results)} videos")
            log("=" * 60)
            
        else:
            # Single file mode
            if not input_path.is_file():
                print(f"Error: {input_path} is not a file", file=sys.stderr)
                sys.exit(1)
            
            log("=" * 60)
            log("VIDEO2MP4 - Single File Conversion")
            log("=" * 60)
            
            result = convert_video(
                input_path,
                output_path=args.output,
                fps=args.fps,
                codec=args.codec,
                audio_codec=args.audio_codec,
                on_progress=log
            )
            
            log("\n" + "=" * 60)
            log(f"Output: {result}")
            log("=" * 60)
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
