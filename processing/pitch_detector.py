# Pitch Detector

"""YIN pitch detection algorithm implementation."""

from dataclasses import dataclass

import numpy as np

from config.defaults import PitchDetectorSettings


@dataclass
class PitchResult:
    """Result of pitch detection."""

    frequency: float  # Fundamental frequency in Hz (0 if unvoiced)
    confidence: float  # Confidence 0.0-1.0
    voiced: bool  # True if pitched sound detected
    rms: float  # RMS energy of frame
    period_samples: int = 0  # Period in samples


class YINPitchDetector:
    """YIN fundamental frequency estimator.

    Based on: Cheveigné, A., & Kawahara, H. (2002).
    "YIN, a fundamental frequency estimator for speech and music."
    """

    def __init__(self, settings: PitchDetectorSettings):
        self.settings = settings
        self.sample_rate = 48000  # Will be set in process or via setter

        # Frame parameters
        self.frame_size = settings.frame_size
        self.hop_size = settings.hop_size
        self.min_freq = settings.min_freq
        self.max_freq = settings.max_freq
        self.threshold = settings.threshold
        self.rms_threshold = 10 ** (settings.rms_threshold_db / 20)

        # Derived limits
        self.min_period = int(self.sample_rate / self.max_freq)
        self.max_period = int(self.sample_rate / self.min_freq)
        self.max_period = min(self.max_period, self.frame_size // 2)

        # Internal buffers (pre-allocated)
        self._buffer = np.zeros(self.frame_size, dtype=np.float32)
        self._buffer_pos = 0
        self._yin_buffer = np.zeros(self.max_period + 1, dtype=np.float32)
        self._cmnd_buffer = np.zeros(self.max_period + 1, dtype=np.float32)

        # State
        self._last_result = PitchResult(0.0, 0.0, False, 0.0)
        self._frames_since_voiced = 0
        self._smoothed_freq = 0.0
        self._smoothing_alpha = 0.3

    def set_sample_rate(self, sample_rate: int):
        """Update sample rate and recalculate limits."""
        self.sample_rate = sample_rate
        self.min_period = int(self.sample_rate / self.max_freq)
        self.max_period = int(self.sample_rate / self.min_freq)
        self.max_period = min(self.max_period, self.frame_size // 2)
        # Reallocate buffers if needed
        if len(self._yin_buffer) < self.max_period + 1:
            self._yin_buffer = np.zeros(self.max_period + 1, dtype=np.float32)
            self._cmnd_buffer = np.zeros(self.max_period + 1, dtype=np.float32)

    def process(self, audio_block: np.ndarray) -> PitchResult:
        """Process audio block and return pitch estimate.

        Accumulates blocks until frame_size is reached, then runs YIN.
        Returns most recent result for each call.

        Args:
            audio_block: Input audio of shape (n_samples,) or (n_samples, channels)

        Returns:
            PitchResult with frequency, confidence, voiced flag
        """
        # Handle multi-channel
        if audio_block.ndim > 1:
            audio_block = np.mean(audio_block, axis=1)

        # Add to internal buffer
        n = len(audio_block)
        remaining = n
        pos = 0

        while remaining > 0:
            space = self.frame_size - self._buffer_pos
            chunk = min(remaining, space)

            self._buffer[self._buffer_pos : self._buffer_pos + chunk] = audio_block[
                pos : pos + chunk
            ]
            self._buffer_pos += chunk
            remaining -= chunk
            pos += chunk

            # Process frame when full
            if self._buffer_pos >= self.frame_size:
                self._run_yin()
                # Shift buffer by hop_size
                self._buffer[: self.frame_size - self.hop_size] = self._buffer[
                    self.hop_size : self.frame_size
                ]
                self._buffer_pos = self.frame_size - self.hop_size

        return self._last_result

    def _run_yin(self):
        """Run YIN algorithm on current frame."""
        frame = self._buffer

        # Calculate RMS
        rms = np.sqrt(np.mean(frame**2))

        # Silence gate
        if rms < self.rms_threshold:
            self._last_result = PitchResult(0.0, 0.0, False, rms)
            self._frames_since_voiced += 1
            if self._frames_since_voiced > 3:
                self._smoothed_freq = 0.0
            return

        # Step 1: Difference function
        # d(tau) = sum((x[n] - x[n+tau])^2) for n=0..W-tau
        # Optimized using: d(tau) = r(0) + r(tau) - 2*r(tau) where r is autocorr
        # But we'll use the direct formulation for clarity

        max_tau = self.max_period
        W = self.frame_size

        # Pre-compute cumulative sums for fast difference calculation
        # d(tau) = sum_{n=0}^{W-tau-1} (x[n] - x[n+tau])^2
        #        = sum x[n]^2 + sum x[n+tau]^2 - 2*sum x[n]*x[n+tau]

        # Use FFT-based autocorrelation for efficiency
        # But for small frame sizes, direct is fine

        # Direct difference function (vectorized)
        for tau in range(self.min_period, max_tau + 1):
            diff = frame[: W - tau] - frame[tau:W]
            self._yin_buffer[tau] = np.sum(diff * diff)

        # Step 2: Cumulative mean normalized difference
        # d'(tau) = d(tau) / (1/tau * sum_{j=1}^{tau} d(j))
        self._cmnd_buffer[self.min_period] = 1.0  # tau=0 case
        running_sum = 0.0

        for tau in range(self.min_period, max_tau + 1):
            running_sum += self._yin_buffer[tau]
            if running_sum > 0:
                self._cmnd_buffer[tau] = self._yin_buffer[tau] * tau / running_sum
            else:
                self._cmnd_buffer[tau] = 1.0

        # Step 3: Absolute threshold
        # Find first minimum below threshold
        tau_estimate = -1
        for tau in range(self.min_period + 1, max_tau + 1):
            if self._cmnd_buffer[tau] < self.threshold:
                # Check if it's a local minimum
                if (
                    tau == self.min_period + 1
                    or self._cmnd_buffer[tau] < self._cmnd_buffer[tau - 1]
                ):
                    # Parabolic interpolation for sub-sample accuracy
                    tau_estimate = self._parabolic_interpolation(tau)
                    break

        # Step 4: If no threshold crossing, use global minimum
        if tau_estimate < 0:
            min_idx = np.argmin(self._cmnd_buffer[self.min_period : max_tau + 1]) + self.min_period
            if self._cmnd_buffer[min_idx] < 1.0:
                tau_estimate = self._parabolic_interpolation(min_idx)

        # Step 5: Calculate frequency and confidence
        if tau_estimate > 0:
            frequency = self.sample_rate / tau_estimate
            confidence = 1.0 - self._cmnd_buffer[int(tau_estimate)]

            # Validate frequency range
            if self.min_freq <= frequency <= self.max_freq:
                self._frames_since_voiced = 0

                # Temporal smoothing
                if self._smoothed_freq > 0:
                    frequency = (
                        1 - self._smoothing_alpha
                    ) * self._smoothed_freq + self._smoothing_alpha * frequency
                self._smoothed_freq = frequency

                self._last_result = PitchResult(
                    frequency=frequency,
                    confidence=confidence,
                    voiced=True,
                    rms=rms,
                    period_samples=int(round(tau_estimate)),
                )
                return

        # Unvoiced
        self._last_result = PitchResult(0.0, 0.0, False, rms)
        self._frames_since_voiced += 1
        if self._frames_since_voiced > 3:
            self._smoothed_freq = 0.0

    def _parabolic_interpolation(self, tau: int) -> float:
        """Parabolic interpolation for sub-sample period estimation."""
        if tau <= self.min_period or tau >= self.max_period:
            return float(tau)

        y1 = self._cmnd_buffer[tau - 1]
        y2 = self._cmnd_buffer[tau]
        y3 = self._cmnd_buffer[tau + 1]

        # Parabolic peak interpolation
        # x = -0.5 * (y3 - y1) / (y1 - 2*y2 + y3)
        denom = y1 - 2 * y2 + y3
        if abs(denom) < 1e-10:
            return float(tau)

        delta = -0.5 * (y3 - y1) / denom
        return tau + delta

    def reset(self):
        """Reset detector state."""
        self._buffer.fill(0)
        self._buffer_pos = 0
        self._last_result = PitchResult(0.0, 0.0, False, 0.0)
        self._frames_since_voiced = 0
        self._smoothed_freq = 0.0


class PitchDetector:
    """High-level pitch detector interface."""

    def __init__(self, sample_rate: int, settings: PitchDetectorSettings | None = None):
        self.settings = settings or PitchDetectorSettings()
        self.detector = YINPitchDetector(self.settings)
        self.detector.set_sample_rate(sample_rate)

    def process(self, audio_block: np.ndarray) -> PitchResult:
        """Process audio block and return pitch estimate."""
        return self.detector.process(audio_block)

    def reset(self):
        self.detector.reset()

    @property
    def frame_size(self) -> int:
        return self.settings.frame_size

    @property
    def hop_size(self) -> int:
        return self.settings.hop_size
