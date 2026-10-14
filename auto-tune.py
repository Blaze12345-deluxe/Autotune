#!/usr/bin/env python3
"""
Real-time Python Auto-Tune & Harmoniser

Capture microphone audio, process it with Auto-Tune (pitch correction)
or Harmoniser (harmony generation), and output through speakers/headphones.
Also supports offline file processing for audio and video files.
"""

import argparse
import sys
import time
import subprocess
import tempfile
import os
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

from audio import (
    AudioEngine,
    AudioInput,
    AudioOutput,
    find_device,
    list_input_devices,
    list_output_devices,
)
from config.defaults import (
    AudioSettings,
    AutoTuneSettings,
    HarmoniserSettings,
    Settings,
)
from music import VALID_KEYS, VALID_SCALES
from processing import AutoTuneProcessor, HarmoniserProcessor

__version__ = "0.1.0"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="auto-tune",
        description="Real-time vocal Auto-Tune & Harmoniser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Utility flags (work without mode)
    parser.add_argument(
        "--list-devices", action="store_true", help="List available audio devices and exit"
    )
    parser.add_argument(
        "--list-scales", action="store_true", help="List available musical scales and exit"
    )

    # Mode selection (mutually exclusive, required unless utility flag)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--autotune", action="store_true", help="Enable pitch correction (Auto-Tune mode)"
    )
    mode_group.add_argument(
        "--harmonise", action="store_true", help="Enable harmony generation (Harmoniser mode)"
    )

    # Musical settings
    parser.add_argument("--key", default="C", choices=VALID_KEYS, help="Musical key (default: C)")
    parser.add_argument(
        "--scale", default="major", choices=VALID_SCALES, help="Musical scale (default: major)"
    )

    # Audio device settings
    parser.add_argument(
        "--input-device",
        type=str,
        default=None,
        help="Input device ID or name substring (default: system default)",
    )
    parser.add_argument(
        "--output-device",
        type=str,
        default=None,
        help="Output device ID or name substring (default: system default)",
    )
    parser.add_argument(
        "--sample-rate", type=int, default=48000, help="Sample rate in Hz (default: 48000)"
    )
    parser.add_argument(
        "--block-size", type=int, default=256, help="Block size in samples (default: 256)"
    )
    parser.add_argument(
        "--channels", type=int, default=1, help="Number of input channels (default: 1)"
    )

    # Auto-Tune options
    parser.add_argument(
        "--correction-speed",
        type=float,
        default=0.5,
        help="Correction speed 0.0-1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--threshold", type=float, default=25.0, help="Correction threshold in cents (default: 25)"
    )

    # Harmoniser options
    parser.add_argument(
        "--intervals",
        type=str,
        default="3,7",
        help="Semitone intervals for harmonies, comma-separated (default: 3,7)",
    )
    parser.add_argument(
        "--voice-volumes",
        type=str,
        default="1.0,0.7,0.7",
        help="Voice volumes, comma-separated (default: 1.0,0.7,0.7)",
    )
    parser.add_argument(
        "--chord-mode",
        choices=["intervals", "scale", "chord"],
        default="intervals",
        help="Harmony generation mode (default: intervals)",
    )
    parser.add_argument(
        "--chord-quality", default="major", help="Chord quality for chord mode (default: major)"
    )

    # File processing options
    parser.add_argument(
        "--input-file", type=str, help="Input audio/video file to process (offline mode)"
    )
    parser.add_argument(
        "--output-file", type=str, help="Output audio file (required with --input-file)"
    )
    parser.add_argument(
        "--keep-video",
        action="store_true",
        help="Keep video stream when processing video file (requires ffmpeg)",
    )

    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity (use -v, -vv, -vvv)"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args()


def build_settings(args: argparse.Namespace) -> Settings:
    """Build Settings object from parsed arguments."""
    # Parse intervals
    try:
        intervals = tuple(int(x.strip()) for x in args.intervals.split(","))
    except ValueError:
        intervals = (3, 7)

    # Parse voice volumes
    try:
        voice_volumes = tuple(float(x.strip()) for x in args.voice_volumes.split(","))
    except ValueError:
        voice_volumes = (1.0, 0.7, 0.7)

    settings = Settings(
        audio=AudioSettings(
            sample_rate=args.sample_rate,
            block_size=args.block_size,
            input_device=args.input_device,
            output_device=args.output_device,
            channels=args.channels,
        ),
        mode="autotune" if args.autotune else "harmonise",
        autotune=AutoTuneSettings(
            key=args.key,
            scale=args.scale,
            correction_speed=args.correction_speed,
            threshold_cents=args.threshold,
        ),
        harmoniser=HarmoniserSettings(
            key=args.key,
            scale=args.scale,
            intervals=intervals,
            voice_volumes=voice_volumes,
            chord_mode=args.chord_mode,
            chord_quality=args.chord_quality,
        ),
        verbose=args.verbose,
    )
    return settings


def list_devices():
    """List available audio devices."""
    print("Input Devices:")
    print("-" * 60)
    default_in = None
    try:
        default_in = AudioInput()._get_default_device()
    except:
        pass

    for dev in list_input_devices():
        marker = " (default)" if dev == default_in else ""
        print(f"  {dev.index:3d}: {dev.name}{marker}")
        print(
            f"        {dev.max_input_channels} in, {dev.max_output_channels} out @ {dev.default_sample_rate:.0f}Hz"
        )

    print("\nOutput Devices:")
    print("-" * 60)
    default_out = None
    try:
        default_out = AudioOutput()._get_default_device()
    except:
        pass

    for dev in list_output_devices():
        marker = " (default)" if dev == default_out else ""
        print(f"  {dev.index:3d}: {dev.name}{marker}")
        print(
            f"        {dev.max_input_channels} in, {dev.max_output_channels} out @ {dev.default_sample_rate:.0f}Hz"
        )


def list_scales():
    """List available musical scales."""
    print("Available Scales:")
    print("-" * 40)
    for scale in sorted(VALID_SCALES):
        print(f"  {scale}")


def resolve_device(device_arg: str | None, input_device: bool = True):
    """Resolve device argument to DeviceInfo."""
    if device_arg is None:
        return None

    # Try as index
    try:
        idx = int(device_arg)
        if input_device:
            devices = list_input_devices()
        else:
            devices = list_output_devices()
        if 0 <= idx < len(devices):
            return devices[idx]
    except ValueError:
        pass

    # Try as name substring
    return find_device(device_arg, input_only=input_device, output_only=not input_device)


def create_processor(settings: Settings, sample_rate: int, block_size: int):
    """Create the appropriate processor based on mode."""
    if settings.mode == "autotune":
        return AutoTuneProcessor(settings.autotune, sample_rate, block_size)
    elif settings.mode == "harmonise":
        return HarmoniserProcessor(settings.harmoniser, sample_rate, block_size)
    else:
        raise ValueError(f"Unknown mode: {settings.mode}")


def print_settings(settings: Settings):
    """Print current settings."""
    print(f"Mode: {settings.mode}")
    print(f"Key: {settings.autotune.key} {settings.autotune.scale}")
    print(f"Sample Rate: {settings.audio.sample_rate} Hz")
    print(f"Block Size: {settings.audio.block_size} samples")

    if settings.mode == "autotune":
        print(f"Correction Speed: {settings.autotune.correction_speed}")
        print(f"Threshold: {settings.autotune.threshold_cents} cents")
    else:
        print(f"Intervals: {settings.harmoniser.intervals}")
        print(f"Voice Volumes: {settings.harmoniser.voice_volumes}")
        print(f"Chord Mode: {settings.harmoniser.chord_mode}")


def extract_audio_from_video(video_path: str, output_path: str, sample_rate: int) -> bool:
    """Extract audio from video file using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-ar", str(sample_rate),
            "-ac", "1",
            "-c:a", "pcm_f32le",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg to process video files.", file=sys.stderr)
        return False


def combine_audio_with_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """Combine processed audio with original video using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: ffmpeg not found.", file=sys.stderr)
        return False


def process_file(
    input_path: str,
    output_path: str,
    processor,
    sample_rate: int,
    block_size: int,
    keep_video: bool = False,
    verbose: int = 0,
) -> int:
    """Process an audio or video file offline."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Create temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        audio_input = tmpdir / "input_audio.wav"
        audio_output = tmpdir / "output_audio.wav"

        # Check if input is video
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v"}
        is_video = input_path.suffix.lower() in video_extensions

        if is_video:
            if verbose > 0:
                print(f"Extracting audio from video: {input_path}")
            if not extract_audio_from_video(str(input_path), str(audio_input), sample_rate):
                return 1
        else:
            # Copy audio file to temp location for uniform processing
            shutil.copy2(input_path, audio_input)

        # Read audio file
        if verbose > 0:
            print(f"Reading audio: {audio_input}")

        try:
            audio_data, file_sr = sf.read(audio_input, dtype="float32")
        except Exception as e:
            print(f"Error reading audio file: {e}", file=sys.stderr)
            return 1

        # Resample if needed
        if file_sr != sample_rate:
            if verbose > 0:
                print(f"Resampling from {file_sr}Hz to {sample_rate}Hz")
            from scipy.signal import resample
            ratio = sample_rate / file_sr
            n_samples = int(len(audio_data) * ratio)
            audio_data = resample(audio_data, n_samples)

        # Ensure mono
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Process in blocks
        n_samples = len(audio_data)
        n_blocks = (n_samples + block_size - 1) // block_size
        output_data = np.zeros_like(audio_data)

        if verbose > 0:
            print(f"Processing {n_blocks} blocks ({n_samples} samples)...")

        for i in range(n_blocks):
            start = i * block_size
            end = min(start + block_size, n_samples)
            block = audio_data[start:end]

            # Pad last block if needed
            if len(block) < block_size:
                block = np.pad(block, (0, block_size - len(block)))

            # Process block
            processed = processor.process(block.reshape(-1, 1), sample_rate).flatten()

            # Trim if last block was padded
            if end > n_samples:
                processed = processed[:end - start]

            output_data[start:end] = processed

            if verbose > 1:
                progress = (i + 1) / n_blocks * 100
                print(f"\rProgress: {progress:.1f}%", end="", flush=True)

        if verbose > 1:
            print()

        # Write processed audio
        if verbose > 0:
            print(f"Writing audio: {audio_output}")
        sf.write(audio_output, output_data, sample_rate, subtype="FLOAT")

        # Handle output
        if is_video and keep_video:
            if verbose > 0:
                print("Combining processed audio with video...")
            if not combine_audio_with_video(str(input_path), str(audio_output), str(output_path)):
                return 1
        else:
            # Just copy the processed audio to output
            shutil.copy2(audio_output, output_path)

    if verbose > 0:
        print(f"Done! Output saved to: {output_path}")
    return 0


def extract_audio_from_video(video_path: str, output_path: str, sample_rate: int) -> bool:
    """Extract audio from video file using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-ar", str(sample_rate),
            "-ac", "1",
            "-c:a", "pcm_f32le",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg to process video files.", file=sys.stderr)
        return False


def combine_audio_with_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """Combine processed audio with original video using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: ffmpeg not found.", file=sys.stderr)
        return False


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Handle utility commands
    if args.list_devices:
        list_devices()
        return 0

    if args.list_scales:
        list_scales()
        return 0

    # File processing mode
    if args.input_file:
        if not args.output_file:
            print("Error: --output-file is required when using --input-file", file=sys.stderr)
            return 2

        if not args.autotune and not args.harmonise:
            print("Error: one of the arguments --autotune --harmonise is required", file=sys.stderr)
            return 2

        settings = build_settings(args)

        if args.verbose > 0:
            print_settings(settings)
            print()

        try:
            processor = create_processor(
                settings, settings.audio.sample_rate, settings.audio.block_size
            )
        except Exception as e:
            print(f"Error creating processor: {e}", file=sys.stderr)
            return 4

        return process_file(
            args.input_file,
            args.output_file,
            processor,
            settings.audio.sample_rate,
            settings.audio.block_size,
            keep_video=args.keep_video,
            verbose=args.verbose,
        )

    # Real-time mode
    if not args.autotune and not args.harmonise:
        print("Error: one of the arguments --autotune --harmonise is required", file=sys.stderr)
        return 2

    settings = build_settings(args)

    # Resolve devices
    input_device = resolve_device(settings.audio.input_device, input_device=True)
    output_device = resolve_device(settings.audio.output_device, input_device=False)

    # Print settings if verbose
    if args.verbose > 0:
        print_settings(settings)
        if input_device:
            print(f"Input Device: {input_device.name}")
        if output_device:
            print(f"Output Device: {output_device.name}")
        print()

    # Create processor
    try:
        processor = create_processor(
            settings, settings.audio.sample_rate, settings.audio.block_size
        )
    except Exception as e:
        print(f"Error creating processor: {e}", file=sys.stderr)
        return 4

    # Create and run engine
    engine = AudioEngine(processor, settings)

    # Set up error callback
    def error_callback(e: Exception):
        if args.verbose > 1:
            print(f"Processing error: {e}", file=sys.stderr)

    engine.set_error_callback(error_callback)

    # Print startup message
    if args.verbose > 0:
        print(f"Starting {settings.mode}...")
        print("Press Ctrl+C to stop")
        print()

    try:
        engine.start()

        if args.verbose > 1:
            # Run with stats display
            last_stats_time = time.time()
            while engine.running:
                time.sleep(0.5)
                if args.verbose > 1 and time.time() - last_stats_time > 2.0:
                    stats = engine.get_stats()
                    print(
                        f"Blocks: {stats['blocks_processed']} | "
                        f"In Overruns: {stats['input']['overruns']} | "
                        f"Out Underruns: {stats['output']['underruns']} | "
                        f"Proc: {stats['avg_processing_time_ms']:.2f}ms | "
                        f"Latency: {stats['processor_latency_ms']:.1f}ms"
                    )
                    last_stats_time = time.time()
        else:
            # Simple wait
            engine.run()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if args.verbose > 0:
            print("\nStopping...")
            stats = engine.get_stats()
            print(f"Blocks processed: {stats['blocks_processed']}")
            print(f"Input overruns: {stats['input']['overruns']}")
            print(f"Output underruns: {stats['output']['underruns']}")
            print(f"Avg processing: {stats['avg_processing_time_ms']:.2f} ms")
            print(f"Max processing: {stats['max_processing_time_ms']:.2f} ms")
            print(f"Processor latency: {stats['processor_latency_ms']:.1f} ms")
        engine.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())