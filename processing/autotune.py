# Auto-Tune Processor

"""Auto-Tune pitch correction processor."""

from dataclasses import dataclass

import numpy as np

from config.defaults import AutoTuneSettings, PitchDetectorSettings, PitchShifterSettings
from music import cents_to_scale, freq_to_midi, midi_to_freq, quantize_to_scale

from .base import AudioProcessor
from .pitch_detector import PitchDetector
from .pitch_shifter import PitchShifter


@dataclass
class CorrectionSmoother:
    """Exponential smoothing for pitch correction."""

    speed: float
    sample_rate: int
    block_size: int

    def __post_init__(self):
        # Time constant: speed=0 -> 1000ms, speed=1 -> 5ms
        tau_ms = 1000 * (1 - self.speed) + 5
        tau_samples = tau_ms * self.sample_rate / 1000
        self.alpha = 1 - np.exp(-self.block_size / tau_samples)
        self.current_ratio = 1.0

    def process(self, target_ratio: float) -> float:
        """Smooth toward target ratio."""
        self.current_ratio += self.alpha * (target_ratio - self.current_ratio)
        return self.current_ratio

    def reset(self):
        self.current_ratio = 1.0

    def update_speed(self, speed: float):
        self.speed = speed
        tau_ms = 1000 * (1 - speed) + 5
        tau_samples = tau_ms * self.sample_rate / 1000
        self.alpha = 1 - np.exp(-self.block_size / tau_samples)


class AutoTuneProcessor(AudioProcessor):
    """Real-time Auto-Tune pitch correction processor."""

    def __init__(
        self,
        settings: AutoTuneSettings,
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
        self.pitch_shifter = PitchShifter(shifter_settings, sample_rate)

        # Smoother
        self.smoother = CorrectionSmoother(settings.correction_speed, sample_rate, block_size)

        # Scale notes cache
        self._scale_key = settings.key
        self._scale_type = settings.scale
        self._scale_notes = None
        self._update_scale()

        # State
        self._last_correction_cents = 0.0
        self._consecutive_unvoiced = 0

    def _update_scale(self):
        """Update cached scale notes."""
        self._scale_notes = quantize_to_scale(
            69, self.settings.key, self.settings.scale  # Dummy midi, just to get scale
        )
        # Actually get all scale notes
        from music.scales import get_scale_notes

        self._scale_notes = get_scale_notes(self.settings.key, self.settings.scale)

    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply pitch correction to audio block."""
        # 1. Detect pitch
        pitch_result = self.pitch_detector.process(audio_block)

        # 2. If not voiced or silent, pass through (with dry mix)
        if not pitch_result.voiced:
            self._consecutive_unvoiced += 1
            if self._consecutive_unvoiced > 2:
                self.smoother.reset()
            # Return dry mix
            if self.settings.mix < 1.0:
                return audio_block * (1 - self.settings.mix) + audio_block * self.settings.mix
            return audio_block

        self._consecutive_unvoiced = 0

        # 3. Quantize to scale
        detected_freq = pitch_result.frequency
        self._quantize_to_scale(detected_freq)

        # 4. Calculate correction in cents
        cents_off = cents_to_scale(detected_freq, self.settings.key, self.settings.scale)

        # 5. Apply threshold
        if abs(cents_off) < self.settings.threshold_cents:
            # Within threshold - no correction
            if self.settings.mix < 1.0:
                return audio_block
            return audio_block

        # 6. Limit maximum correction
        cents_off = np.clip(
            cents_off, -self.settings.max_correction_cents, self.settings.max_correction_cents
        )

        # 7. Convert to ratio
        target_ratio = 2.0 ** (cents_off / 1200.0)

        # 8. Smooth correction
        smoothed_ratio = self.smoother.process(target_ratio)

        # 9. Apply pitch shift
        if abs(smoothed_ratio - 1.0) > 0.001:
            corrected = self.pitch_shifter.shift_streaming(audio_block, smoothed_ratio)
        else:
            corrected = audio_block

        # 10. Wet/dry mix
        if self.settings.mix < 1.0:
            output = corrected * self.settings.mix + audio_block * (1 - self.settings.mix)
        else:
            output = corrected

        self._last_correction_cents = cents_off
        return output

    def _quantize_to_scale(self, frequency: float) -> float:
        """Quantize frequency to nearest scale note."""
        if frequency <= 0:
            return 0.0

        midi = freq_to_midi(frequency)
        quantized_midi = quantize_to_scale(midi, self.settings.key, self.settings.scale)
        return midi_to_freq(quantized_midi)

    def reset(self):
        self.pitch_detector.reset()
        self.pitch_shifter.reset()
        self.smoother.reset()
        self._consecutive_unvoiced = 0
        self._last_correction_cents = 0.0

    def update_settings(self, settings: AutoTuneSettings):
        """Update settings at runtime."""
        self.settings = settings
        self.smoother.update_speed(settings.correction_speed)

        if settings.key != self._scale_key or settings.scale != self._scale_type:
            self._scale_key = settings.key
            self._scale_type = settings.scale
            self._update_scale()

    @property
    def latency_samples(self) -> int:
        return self.pitch_shifter.latency_samples + self.pitch_detector.frame_size

    @property
    def name(self) -> str:
        return "AutoTune"

    def get_debug_info(self) -> dict:
        """Get debug information."""
        return {
            "last_correction_cents": self._last_correction_cents,
            "consecutive_unvoiced": self._consecutive_unvoiced,
            "smoother_ratio": self.smoother.current_ratio,
            "scale_key": self._scale_key,
            "scale_type": self._scale_type,
        }


def create_autotune_processor(
    settings: AutoTuneSettings,
    sample_rate: int,
    block_size: int,
) -> AutoTuneProcessor:
    """Factory function for AutoTuneProcessor."""
    return AutoTuneProcessor(settings, sample_rate, block_size)


# Register with factory
from .base import ProcessorFactory

ProcessorFactory.register("autotune", create_autotune_processor)
