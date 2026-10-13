#!/usr/bin/env python3
"""
Real-time Python Auto-Tune & Harmoniser

Capture microphone audio, process it with Auto-Tune (pitch correction) 
or Harmoniser (harmony generation), and output through speakers/headphones.
"""

import argparse
import signal
import sys
import time
from typing import Optional

import numpy as np

from config.defaults import (
    Settings, AudioSettings, AutoTuneSettings, HarmoniserSettings,
    PitchDetectorSettings, PitchShifterSettings
)
from audio import AudioEngine, AudioInput, AudioOutput, list_input_devices, list_output_devices, find_device
from processing import AutoTuneProcessor, HarmoniserProcessor, ProcessorFactory
from music import VALID_KEYS, VALID_SCALES


__version__ = "0.1.0"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='auto-tune',
        description='Real-time vocal Auto-Tune & Harmoniser',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Mode selection (mutually exclusive, required)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--autotune', action='store_true',
        help='Enable pitch correction (Auto-Tune mode)'
    )
    mode_group.add_argument(
        '--harmonise', action='store_true',
        help='Enable harmony generation (Harmoniser mode)'
    )
    
    # Musical settings
    parser.add_argument(
        '--key', default='C', choices=VALID_KEYS,
        help='Musical key (default: C)'
    )
    parser.add_argument(
        '--scale', default='major', choices=VALID_SCALES,
        help='Musical scale (default: major)'
    )
    
    # Audio device settings
    parser.add_argument(
        '--input-device', type=str, default=None,
        help='Input device ID or name substring (default: system default)'
    )
    parser.add_argument(
        '--output-device', type=str, default=None,
        help='Output device ID or name substring (default: system default)'
    )
    parser.add_argument(
        '--sample-rate', type=int, default=48000,
        help='Sample rate in Hz (default: 48000)'
    )
    parser.add_argument(
        '--block-size', type=int, default=256,
        help='Block size in samples (default: 256)'
    )
    parser.add_argument(
        '--channels', type=int, default=1,
        help='Number of input channels (default: 1)'
    )
    
    # Auto-Tune options
    parser.add_argument(
        '--correction-speed', type=float, default=0.5,
        help='Correction speed 0.0-1.0 (default: 0.5)'
    )
    parser.add_argument(
        '--threshold', type=float, default=25.0,
        help='Correction threshold in cents (default: 25)'
    )
    
    # Harmoniser options
    parser.add_argument(
        '--intervals', type=str, default='3,7',
        help='Semitone intervals for harmonies, comma-separated (default: 3,7)'
    )
    parser.add_argument(
        '--voice-volumes', type=str, default='1.0,0.7,0.7',
        help='Voice volumes, comma-separated (default: 1.0,0.7,0.7)'
    )
    parser.add_argument(
        '--chord-mode', choices=['intervals', 'scale', 'chord'],
        default='intervals',
        help='Harmony generation mode (default: intervals)'
    )
    parser.add_argument(
        '--chord-quality', default='major',
        help='Chord quality for chord mode (default: major)'
    )
    
    # Utility
    parser.add_argument(
        '--list-devices', action='store_true',
        help='List available audio devices and exit'
    )
    parser.add_argument(
        '--list-scales', action='store_true',
        help='List available musical scales and exit'
    )
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Increase verbosity (use -v, -vv, -vvv)'
    )
    parser.add_argument(
        '--version', action='version',
        version=f'%(prog)s {__version__}'
    )
    
    return parser.parse_args()


def build_settings(args: argparse.Namespace) -> Settings:
    """Build Settings object from parsed arguments."""
    # Parse intervals
    try:
        intervals = tuple(int(x.strip()) for x in args.intervals.split(','))
    except ValueError:
        intervals = (3, 7)
    
    # Parse voice volumes
    try:
        voice_volumes = tuple(float(x.strip()) for x in args.voice_volumes.split(','))
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
        mode='autotune' if args.autotune else 'harmonise',
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
        print(f"        {dev.max_input_channels} in, {dev.max_output_channels} out @ {dev.default_sample_rate:.0f}Hz")
    
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
        print(f"        {dev.max_input_channels} in, {dev.max_output_channels} out @ {dev.default_sample_rate:.0f}Hz")


def list_scales():
    """List available musical scales."""
    print("Available Scales:")
    print("-" * 40)
    for scale in sorted(VALID_SCALES):
        print(f"  {scale}")


def resolve_device(device_arg: Optional[str], input_device: bool = True):
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
    if settings.mode == 'autotune':
        return AutoTuneProcessor(
            settings.autotune, sample_rate, block_size
        )
    elif settings.mode == 'harmonise':
        return HarmoniserProcessor(
            settings.harmoniser, sample_rate, block_size
        )
    else:
        raise ValueError(f"Unknown mode: {settings.mode}")


def print_settings(settings: Settings):
    """Print current settings."""
    print(f"Mode: {settings.mode}")
    print(f"Key: {settings.autotune.key} {settings.autotune.scale}")
    print(f"Sample Rate: {settings.audio.sample_rate} Hz")
    print(f"Block Size: {settings.audio.block_size} samples")
    
    if settings.mode == 'autotune':
        print(f"Correction Speed: {settings.autotune.correction_speed}")
        print(f"Threshold: {settings.autotune.threshold_cents} cents")
    else:
        print(f"Intervals: {settings.harmoniser.intervals}")
        print(f"Voice Volumes: {settings.harmoniser.voice_volumes}")
        print(f"Chord Mode: {settings.harmoniser.chord_mode}")


def main():
    """Main entry point."""
    args = parse_args()
    
    # Handle utility commands
    if args.list_devices:
        list_devices()
        return 0
    
    if args.list_scales:
        list_scales()
        return 0
    
    # Build settings
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
        processor = create_processor(settings, settings.audio.sample_rate, settings.audio.block_size)
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
        print(f"Press Ctrl+C to stop")
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
                    print(f"Blocks: {stats['blocks_processed']} | "
                          f"In Overruns: {stats['input']['overruns']} | "
                          f"Out Underruns: {stats['output']['underruns']} | "
                          f"Proc: {stats['avg_processing_time_ms']:.2f}ms | "
                          f"Latency: {stats['processor_latency_ms']:.1f}ms")
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


if __name__ == '__main__':
    sys.exit(main())