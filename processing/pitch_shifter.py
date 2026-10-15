# Pitch Shifter

"""Phase vocoder pitch shifting implementation."""

from dataclasses import dataclass

import numpy as np

from config.defaults import PitchShifterSettings


@dataclass
class PhaseVocoderState:
    """State for streaming phase vocoder."""

    # Analysis
    analysis_buffer: np.ndarray
    analysis_pos: int

    # Synthesis
    synthesis_buffer: np.ndarray
    synthesis_pos: int

    # Phase accumulation
    phase_accumulator: np.ndarray
    previous_phase: np.ndarray

    # Window
    window: np.ndarray
    window_sum: np.ndarray  # For overlap-add normalization


class PitchShifter:
    """Phase vocoder pitch shifter.

    Implements real-time pitch shifting using STFT phase vocoder.
    Preserves timing and (optionally) formants.
    """

    def __init__(self, settings: PitchShifterSettings, sample_rate: int = 48000):
        self.settings = settings
        self.sample_rate = sample_rate

        self.fft_size = settings.fft_size
        self.hop_size = settings.hop_size
        self.window_type = settings.window
        self.preserve_formants = settings.preserve_formants
        self.max_shift_ratio = settings.max_shift_ratio

        # Derived
        self.freq_bins = self.fft_size // 2 + 1
        self.bin_freq = self.sample_rate / self.fft_size

        # Window
        self.window = self._create_window()
        self.window_sum = self._compute_window_sum()

        # Expected phase advance per hop
        self.expected_phase_advance = (
            2 * np.pi * np.arange(self.freq_bins) * self.hop_size / self.fft_size
        )

        # Streaming state
        self.state: PhaseVocoderState | None = None

        # Formant preservation (cepstral)
        self._cepstral_order = 30 if self.preserve_formants else 0

    def _compute_window_sum(self) -> np.ndarray:
        """Compute the sum of squared window overlaps for overlap-add normalization.
        
        For proper overlap-add, we need to compute how many windows overlap at each sample
        and sum their squared values. This avoids out-of-bounds slicing issues.
        """
        window_sq = self.window**2
        window_sum = np.zeros(self.fft_size, dtype=np.float32)
        
        # Number of hops that fit in one FFT frame
        n_hops = self.fft_size // self.hop_size
        
        # For each hop position, add the window contribution
        for hop in range(n_hops):
            start = hop * self.hop_size
            end = start + self.fft_size
            if end <= self.fft_size:
                window_sum[start:end] += window_sq
            else:
                # Handle wrap-around (shouldn't happen with proper hop_size)
                available = self.fft_size - start
                window_sum[start:] += window_sq[:available]
        
        # Avoid division by zero
        window_sum[window_sum == 0] = 1.0
        return window_sum

    def _create_window(self) -> np.ndarray:
        """Create window function."""
        if self.window_type == "hann":
            return np.hanning(self.fft_size).astype(np.float32)
        elif self.window_type == "hamming":
            return np.hamming(self.fft_size).astype(np.float32)
        elif self.window_type == "blackman":
            return np.blackman(self.fft_size).astype(np.float32)
        elif self.window_type == "blackman_harris":
            return np.blackman(self.fft_size).astype(np.float32)  # Approximation
        else:
            return np.hanning(self.fft_size).astype(np.float32)

    def _init_streaming_state(self):
        """Initialize streaming state."""
        self.state = PhaseVocoderState(
            analysis_buffer=np.zeros(self.fft_size, dtype=np.float32),
            analysis_pos=0,
            synthesis_buffer=np.zeros(self.fft_size, dtype=np.float32),
            synthesis_pos=0,
            phase_accumulator=np.zeros(self.freq_bins, dtype=np.float32),
            previous_phase=np.zeros(self.freq_bins, dtype=np.float32),
            window=self.window,
            window_sum=self.window_sum,
        )

    def shift(
        self, audio: np.ndarray, ratio: float, preserve_formants: bool | None = None
    ) -> np.ndarray:
        """Offline pitch shift (entire signal at once).

        Args:
            audio: Input audio signal
            ratio: Pitch shift ratio (>1 = higher, <1 = lower)
            preserve_formants: Override formant preservation setting

        Returns:
            Pitch-shifted audio of same length
        """
        if preserve_formants is None:
            preserve_formants = self.preserve_formants

        ratio = np.clip(ratio, 1.0 / self.max_shift_ratio, self.max_shift_ratio)

        if abs(ratio - 1.0) < 0.001:
            return audio.copy()

        # Ensure audio is 1D (flatten if needed, e.g., from (N, 1) to (N,))
        if audio.ndim > 1:
            audio = audio.flatten()

        # Pad for boundary handling
        pad = self.fft_size
        padded = np.pad(audio, (pad, pad), mode="reflect")

        # STFT
        n_frames = (len(padded) - self.fft_size) // self.hop_size + 1
        stft = np.zeros((n_frames, self.freq_bins), dtype=np.complex64)

        for i in range(n_frames):
            frame = padded[i * self.hop_size : i * self.hop_size + self.fft_size]
            windowed = frame * self.window
            stft[i] = np.fft.rfft(windowed)

        # Phase vocoder processing
        magnitude = np.abs(stft)
        phase = np.angle(stft)

        # Phase unwrapping and true frequency
        phase_diff = np.diff(phase, axis=0, prepend=phase[0:1])
        phase_diff = self._wrap_phase(phase_diff - self.expected_phase_advance)
        true_freq = self.expected_phase_advance + phase_diff

        # Scale frequencies
        true_freq *= ratio

        # Formant preservation
        if preserve_formants and ratio != 1.0:
            magnitude = self._preserve_formants(magnitude, ratio)

        # Reconstruct phase
        new_phase_advance = true_freq
        new_phase = np.cumsum(new_phase_advance, axis=0)
        new_phase = self._wrap_phase(new_phase)

        # ISTFT
        new_stft = magnitude * np.exp(1j * new_phase)

        # Overlap-add
        output_len = len(padded) + self.fft_size
        output = np.zeros(output_len, dtype=np.float32)

        for i in range(n_frames):
            frame = np.fft.irfft(new_stft[i], n=self.fft_size)
            start = i * self.hop_size
            output[start : start + self.fft_size] += frame * self.window

        # Normalize by window sum - compute window sum for the full output length
        # The window sum for overlap-add at each position
        full_window_sum = np.zeros(output_len, dtype=np.float32)
        for i in range(n_frames):
            start = i * self.hop_size
            full_window_sum[start : start + self.fft_size] += self.window**2
        full_window_sum[full_window_sum == 0] = 1.0
        
        # Normalize by window sum
        output = output / full_window_sum

        # Remove padding and match original length
        result = output[pad : pad + len(audio)]

        return result.astype(np.float32)

    def shift_streaming(self, audio_block: np.ndarray, ratio: float) -> np.ndarray:
        """Streaming pitch shift using phase vocoder with proper state management.
        
        This implementation maintains phase continuity across blocks by:
        1. Accumulating input in an analysis buffer until we have a full FFT frame
        2. Processing frames using phase vocoder algorithm with phase accumulator
        3. Using overlap-add synthesis with proper windowing
        4. Maintaining phase accumulator state across blocks
        
        Args:
            audio_block: Input audio block (any length, 1D or 2D with shape (N, 1))
            ratio: Pitch shift ratio
            
        Returns:
            Pitch-shifted block of same length as input
        """
        # Ensure 1D input
        if audio_block.ndim > 1:
            audio_block = audio_block.flatten()
            
        # Initialize state if needed
        if self.state is None:
            self._init_streaming_state()
        
        ratio = np.clip(ratio, 1.0 / self.max_shift_ratio, self.max_shift_ratio)
        
        if abs(ratio - 1.0) < 0.001:
            return audio_block.copy()
        
        n_samples = len(audio_block)
        output = np.zeros(n_samples, dtype=np.float32)
        
        # Process samples one by one, maintaining streaming state
        input_ptr = 0
        output_ptr = 0
        
        while input_ptr < n_samples or self.state.analysis_pos >= self.hop_size:
            # Fill analysis buffer until we have a full hop
            if self.state.analysis_pos < self.hop_size and input_ptr < n_samples:
                space = self.hop_size - self.state.analysis_pos
                chunk_size = min(space, n_samples - input_ptr)
                self.state.analysis_buffer[
                    self.state.analysis_pos:self.state.analysis_pos + chunk_size
                ] = audio_block[input_ptr:input_ptr + chunk_size]
                self.state.analysis_pos += chunk_size
                input_ptr += chunk_size
            
            # Process one hop when we have enough data
            if self.state.analysis_pos >= self.hop_size:
                # Analyze one hop_size frame (padded to fft_size for FFT)
                frame = np.zeros(self.fft_size, dtype=np.float32)
                frame[:self.hop_size] = self.state.analysis_buffer[:self.hop_size] * self.window[:self.hop_size]
                
                # STFT analysis
                spectrum = np.fft.rfft(frame)
                magnitude = np.abs(spectrum)
                phase = np.angle(spectrum)
                
                # Phase difference
                phase_diff = self._wrap_phase(
                    phase - self.state.previous_phase - self.expected_phase_advance
                )
                true_freq = self.expected_phase_advance + phase_diff
                
                # Scale frequency
                true_freq *= ratio
                
                # Formant preservation (simplified)
                if self.preserve_formants and ratio != 1.0:
                    magnitude = self._preserve_formants_streaming(magnitude, ratio)
                
                # Accumulate phase
                self.state.phase_accumulator = self._wrap_phase(
                    self.state.phase_accumulator + true_freq
                )
                
                # Synthesize
                new_spectrum = magnitude * np.exp(1j * self.state.phase_accumulator)
                synth_frame = np.fft.irfft(new_spectrum, n=self.fft_size)
                synth_frame *= self.window
                
                # Overlap-add to synthesis buffer
                self.state.synthesis_buffer += synth_frame
                
                # Output available samples (up to hop_size)
                out_len = min(self.hop_size, n_samples - output_ptr)
                if out_len > 0:
                    out_data = self.state.synthesis_buffer[:out_len]
                    norm = self.window_sum[:out_len]
                    output[output_ptr:output_ptr + out_len] = out_data / norm
                    output_ptr += out_len
                
                # Update state
                self.state.previous_phase = phase
                # Shift analysis buffer by hop_size
                self.state.analysis_buffer[:-self.hop_size] = self.state.analysis_buffer[self.hop_size:]
                self.state.analysis_buffer[-self.hop_size:] = 0
                self.state.analysis_pos = max(0, self.state.analysis_pos - self.hop_size)
                
                # Shift synthesis buffer
                self.state.synthesis_buffer[:-self.hop_size] = self.state.synthesis_buffer[self.hop_size:]
                self.state.synthesis_buffer[-self.hop_size:] = 0
                self.state.synthesis_pos = max(0, self.state.synthesis_pos - self.hop_size)
        
        # If we didn't produce enough output (not enough input for a full hop),
        # the remaining output stays as zeros (silence)
        # This is acceptable for real-time processing
        
        return output

    def _wrap_phase(self, phase: np.ndarray) -> np.ndarray:
        """Wrap phase to [-pi, pi]."""
        return (phase + np.pi) % (2 * np.pi) - np.pi

    def _preserve_formants(self, magnitude: np.ndarray, ratio: float) -> np.ndarray:
        """Preserve formants using cepstral processing."""
        # For each frame, compute cepstrum, warp, and reconstruct
        n_frames = magnitude.shape[0]
        result = np.zeros_like(magnitude)

        for i in range(n_frames):
            # Log magnitude
            log_mag = np.log(magnitude[i] + 1e-10)

            # Cepstrum
            cepstrum = np.fft.irfft(log_mag)

            # Warp cepstrum (liftering)
            if ratio > 1.0:
                # Pitch up: compress cepstrum
                int(len(cepstrum) / ratio)
            else:
                # Pitch down: expand cepstrum
                int(len(cepstrum) * ratio)

            # Keep only low-order cepstral coefficients (formants)
            warped_cepstrum = np.zeros_like(cepstrum)
            keep = min(self._cepstral_order, len(cepstrum))
            warped_cepstrum[:keep] = cepstrum[:keep]

            # Reconstruct
            new_log_mag = np.fft.rfft(warped_cepstrum).real
            result[i] = np.exp(new_log_mag)

        return result

    def _preserve_formants_streaming(self, magnitude: np.ndarray, ratio: float) -> np.ndarray:
        """Simplified formant preservation for streaming."""
        # Simple spectral envelope preservation
        # Compute spectral envelope using linear prediction or cepstrum
        log_mag = np.log(magnitude + 1e-10)
        cepstrum = np.fft.irfft(log_mag)

        # Keep low quefrency (formants)
        cepstrum[self._cepstral_order :] = 0

        # Reconstruct envelope
        envelope = np.exp(np.fft.rfft(cepstrum).real)

        # Apply envelope to shifted magnitude
        # This is a simplified version - real implementation would warp the envelope
        return magnitude * envelope / (np.mean(envelope) + 1e-10)

    def reset(self):
        """Reset streaming state."""
        self.state = None

    @property
    def latency_samples(self) -> int:
        return self.fft_size


class SimplePitchShifter:
    """Simpler pitch shifter using resampling (for testing/fallback).

    Changes pitch by resampling - changes duration too!
    Not suitable for real-time auto-tune, but useful for testing.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

    def shift(self, audio: np.ndarray, ratio: float) -> np.ndarray:
        """Pitch shift by resampling."""
        from scipy.signal import resample

        n_out = int(len(audio) / ratio)
        return resample(audio, n_out).astype(np.float32)

    def shift_streaming(self, audio_block: np.ndarray, ratio: float) -> np.ndarray:
        # Not implemented for streaming
        return self.shift(audio_block, ratio)

    def reset(self):
        pass

    @property
    def latency_samples(self) -> int:
        return 0
