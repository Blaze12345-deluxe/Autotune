# Harmoniser Processor

"""Real-time harmony generation processor."""

from dataclasses import dataclass

import numpy as np

from config.defaults import HarmoniserSettings, PitchDetectorSettings, PitchShifterSettings
from music import (
    apply_harmony_smoothing,
    create_harmony_preset,
    generate_chord_harmonies,
    generate_diatonic_harmonies,
    smooth_voice_leading,
    transpose_freq,
)

from .base import AudioProcessor
from .pitch_detector import PitchDetector
from .pitch_shifter import PitchShifter


@dataclass
class VoiceState:
    """State for a single harmony voice."""

    shifter: PitchShifter
    target_freq: float = 0.0
    current_freq: float = 0.0
    volume: float = 1.0
    active: bool = False


class HarmoniserProcessor(AudioProcessor):
    """Real-time harmony generation processor."""

    def __init__(
        self,
        settings: HarmoniserSettings,
        sample_rate: int,
        block_size: int,
        pitch_detector_settings: PitchDetectorSettings | None = None,
        pitch_shifter_settings: PitchShifterSettings | None = None,
    ):
        self.settings = settings
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Components
        detector_settings = pitch_detector_settings or PitchDetectorSettings()
        self.pitch_detector = PitchDetector(sample_rate, detector_settings)

        shifter_settings = pitch_shifter_settings or PitchShifterSettings()

        # Lead voice (original pitch - may be pitch-corrected)
        self.lead_shifter = PitchShifter(shifter_settings, sample_rate)

        # Harmony voices
        self.harmony_voices: list[VoiceState] = []
        max_harmonies = settings.max_voices - 1  # Excluding lead
        for i in range(max_harmonies):
            self.harmony_voices.append(
                VoiceState(
                    shifter=PitchShifter(shifter_settings, sample_rate),
                    volume=(
                        settings.voice_volumes[i + 1]
                        if i + 1 < len(settings.voice_volumes)
                        else 0.5
                    ),
                )
            )

        # Lead volume
        self.lead_volume = settings.voice_volumes[0] if settings.voice_volumes else 1.0

        # State
        self._last_source_freq = 0.0
        self._last_harmonies: list[float] = []
        self._consecutive_unvoiced = 0

        # Smoothing
        self._harmony_smoothing_alpha = 0.15

    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Generate harmonies from audio block."""
        # 1. Detect pitch
        pitch_result = self.pitch_detector.process(audio_block)

        # 2. If not voiced, pass through lead only
        if not pitch_result.voiced:
            self._consecutive_unvoiced += 1
            if self._consecutive_unvoiced > 2:
                self._reset_harmonies()
            return audio_block * self.lead_volume * self.settings.lead_mix

        self._consecutive_unvoiced = 0
        source_freq = pitch_result.frequency

        # 3. Generate harmony targets based on mode
        if self.settings.chord_mode == "intervals":
            harmony_freqs = self._generate_interval_harmonies(source_freq)
        elif self.settings.chord_mode == "scale":
            harmony_freqs = generate_diatonic_harmonies(
                source_freq, self.settings.key, self.settings.scale
            )
        elif self.settings.chord_mode == "chord":
            harmony_freqs = generate_chord_harmonies(
                source_freq, self.settings.key, self.settings.scale, self.settings.chord_quality
            )
        else:
            harmony_freqs = self._generate_interval_harmonies(source_freq)

        # Limit to available voices
        harmony_freqs = harmony_freqs[: len(self.harmony_voices)]

        # 4. Smooth harmony transitions
        harmony_freqs = smooth_voice_leading(self._last_harmonies, harmony_freqs)
        harmony_freqs = apply_harmony_smoothing(
            harmony_freqs, self._last_harmonies, self._harmony_smoothing_alpha
        )
        self._last_harmonies = harmony_freqs
        self._last_source_freq = source_freq

        # 5. Update voice targets
        for _i, (voice, target_freq) in enumerate(zip(self.harmony_voices, harmony_freqs, strict=False)):
            voice.target_freq = target_freq
            voice.active = target_freq > 0

        # 6. Process lead voice (can apply pitch correction or pass through)
        # For now, pass through with volume
        lead_output = audio_block * self.lead_volume * self.settings.lead_mix

        # 7. Process harmony voices
        harmony_output = np.zeros_like(audio_block)

        for voice in self.harmony_voices:
            if voice.active and voice.volume > 0:
                # Calculate shift ratio
                if source_freq > 0:
                    ratio = voice.target_freq / source_freq
                    ratio = np.clip(ratio, 0.25, 4.0)  # Limit to ±2 octaves

                    # Smooth ratio changes
                    if abs(voice.current_freq - voice.target_freq) > 1.0:
                        voice.current_freq = voice.target_freq

                    harmony = voice.shifter.shift_streaming(audio_block, ratio)
                    harmony_output += harmony * voice.volume
                else:
                    voice.active = False

        # 8. Mix lead + harmonies
        output = lead_output + harmony_output

        # 9. Soft limiting to prevent clipping
        output = self._soft_limit(output)

        return output

    def _generate_interval_harmonies(self, source_freq: float) -> list[float]:
        """Generate harmonies at fixed intervals."""
        harmonies = []
        for interval in self.settings.intervals:
            harmony_freq = transpose_freq(source_freq, interval)
            harmonies.append(harmony_freq)
        return harmonies

    def _soft_limit(self, audio: np.ndarray, threshold: float = 0.95) -> np.ndarray:
        """Apply soft limiting to prevent clipping."""
        peak = np.max(np.abs(audio))
        if peak > threshold:
            # Soft knee compression
            gain = threshold / peak
            # Smooth gain reduction using tanh
            return np.tanh(audio * gain) / np.tanh(gain) * threshold
        return audio

    def _reset_harmonies(self):
        """Reset all harmony voices."""
        self._last_harmonies = []
        self._last_source_freq = 0.0
        for voice in self.harmony_voices:
            voice.target_freq = 0.0
            voice.active = False
            voice.shifter.reset()
        self.lead_shifter.reset()

    def reset(self):
        self.pitch_detector.reset()
        self.lead_shifter.reset()
        for voice in self.harmony_voices:
            voice.shifter.reset()
        self._reset_harmonies()
        self._consecutive_unvoiced = 0

    def update_settings(self, settings: HarmoniserSettings):
        """Update settings at runtime."""
        self.settings = settings

        # Update voice volumes
        for i, voice in enumerate(self.harmony_voices):
            if i + 1 < len(settings.voice_volumes):
                voice.volume = settings.voice_volumes[i + 1]
        self.lead_volume = settings.voice_volumes[0] if settings.voice_volumes else 1.0

    def apply_preset(self, preset_name: str):
        """Apply harmony preset."""
        preset = create_harmony_preset(preset_name)

        self.settings.voice_volumes = preset["voice_volumes"]
        self.settings.intervals = preset["intervals"]
        self.update_settings(self.settings)

    @property
    def latency_samples(self) -> int:
        # Use first harmony voice shifter latency
        if self.harmony_voices:
            return self.harmony_voices[0].shifter.latency_samples + self.pitch_detector.frame_size
        return self.lead_shifter.latency_samples + self.pitch_detector.frame_size

    @property
    def name(self) -> str:
        return "Harmoniser"

    def get_debug_info(self) -> dict:
        """Get debug information."""
        return {
            "source_freq": self._last_source_freq,
            "harmony_freqs": self._last_harmonies,
            "active_voices": sum(1 for v in self.harmony_voices if v.active),
            "chord_mode": self.settings.chord_mode,
            "intervals": self.settings.intervals,
            "voice_volumes": self.settings.voice_volumes,
        }


def create_harmoniser_processor(
    settings: HarmoniserSettings,
    sample_rate: int,
    block_size: int,
) -> HarmoniserProcessor:
    """Factory function for HarmoniserProcessor."""
    return HarmoniserProcessor(settings, sample_rate, block_size)


# Register with factory
from .base import ProcessorFactory

ProcessorFactory.register("harmonise", create_harmoniser_processor)
