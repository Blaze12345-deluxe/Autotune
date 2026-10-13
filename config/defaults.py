# Auto-Tune Configuration

"""Default settings and configuration dataclasses for the Auto-Tune & Harmoniser application."""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
import numpy as np


@dataclass
class PitchDetectorSettings:
    """Configuration for YIN pitch detector."""
    frame_size: int = 2048
    hop_size: int = 512
    min_freq: float = 65.0      # C2
    max_freq: float = 1050.0    # C6
    threshold: float = 0.1
    rms_threshold_db: float = -60.0


@dataclass
class PitchShifterSettings:
    """Configuration for phase vocoder pitch shifter."""
    fft_size: int = 2048
    hop_size: int = 512
    window: str = 'hann'
    preserve_formants: bool = True
    max_shift_ratio: float = 2.0  # ±1 octave


@dataclass
class AutoTuneSettings:
    """Configuration for Auto-Tune processor."""
    key: str = "C"
    scale: str = "major"
    correction_speed: float = 0.5      # 0.0 (slow/natural) to 1.0 (fast/robotic)
    threshold_cents: float = 25.0      # Only correct if off by more than this
    max_correction_cents: float = 600.0  # Max ±600 cents (±5 semitones)
    formant_preserve: bool = True
    mix: float = 1.0                    # Wet/dry mix (1.0 = full correction)


@dataclass
class HarmoniserSettings:
    """Configuration for Harmoniser processor."""
    key: str = "C"
    scale: str = "major"
    intervals: Tuple[int, ...] = (3, 7)      # Semitone intervals (default: minor triad)
    voice_volumes: Tuple[float, ...] = (1.0, 0.7, 0.7)  # Lead, harmony1, harmony2...
    chord_mode: str = "intervals"     # "intervals", "scale", "chord"
    chord_quality: str = "major"      # For chord_mode="chord"
    formant_preserve: bool = True
    lead_mix: float = 1.0
    max_voices: int = 4


@dataclass
class AudioSettings:
    """Audio I/O configuration."""
    sample_rate: int = 48000
    block_size: int = 256
    input_device: Optional[str] = None
    output_device: Optional[str] = None
    channels: int = 1
    input_latency: str = 'low'
    output_latency: str = 'low'


@dataclass
class Settings:
    """Master settings container."""
    audio: AudioSettings = field(default_factory=AudioSettings)
    pitch_detector: PitchDetectorSettings = field(default_factory=PitchDetectorSettings)
    pitch_shifter: PitchShifterSettings = field(default_factory=PitchShifterSettings)
    autotune: AutoTuneSettings = field(default_factory=AutoTuneSettings)
    harmoniser: HarmoniserSettings = field(default_factory=HarmoniserSettings)
    mode: str = "autotune"  # "autotune" | "harmonise"
    verbose: int = 0

    def get_processor_settings(self):
        """Get settings for the active processor."""
        if self.mode == "autotune":
            return self.autotune
        elif self.mode == "harmonise":
            return self.harmoniser
        return None