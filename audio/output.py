# Audio Output

"""Speaker/headphone output handling and device management."""

from collections.abc import Callable

import numpy as np
import sounddevice as sd

from .buffer import RingBuffer
from .input import (
    DeviceInfo,
    get_default_output_device,
    list_output_devices,
    validate_device,
)


class AudioOutput:
    """Speaker/headphone output stream manager."""

    def __init__(
        self,
        device: DeviceInfo | None = None,
        sample_rate: int = 48000,
        block_size: int = 256,
        channels: int = 2,
        latency: str = "low",
        dtype: np.dtype = np.float32,
        buffer_size: int = 4096,
    ):
        """Initialize audio output.

        Args:
            device: Output device (None = default)
            sample_rate: Sample rate in Hz
            block_size: Block size in samples
            channels: Number of output channels
            latency: 'low', 'high', or specific latency in seconds
            dtype: Data type
            buffer_size: Internal ring buffer size (power of 2)
        """
        self.device = device or get_default_output_device()
        self.device = validate_device(self.device, input_required=False)

        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels
        self.dtype = dtype

        # Configure latency
        if latency == "low":
            self.latency = self.device.default_low_output_latency
        elif latency == "high":
            self.latency = self.device.default_high_output_latency
        else:
            self.latency = float(latency)

        # Ring buffer for thread-safe transfer
        self.buffer = RingBuffer(buffer_size, channels, dtype)

        # Stream
        self._stream: sd.OutputStream | None = None
        self._running = False

        # Silence buffer for underruns
        self._silence = np.zeros((block_size, channels), dtype=dtype)

        # Callbacks
        self._underflow_callback = None

    def start(self):
        """Start the output stream."""
        if self._running:
            return

        self._stream = sd.OutputStream(
            device=self.device.index,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=self.channels,
            dtype=self.dtype,
            latency=self.latency,
            callback=self._callback,
            finished_callback=self._finished_callback,
        )
        self._stream.start()
        self._running = True

    def stop(self):
        """Stop the output stream."""
        if not self._running:
            return

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False

    def _callback(
        self, outdata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
    ):
        """Audio callback - runs on PortAudio thread."""
        if status.output_underflow:
            self.buffer.underruns += 1
            if self._underflow_callback:
                self._underflow_callback()

        # Read from ring buffer - ensure we read exactly 'frames' samples
        data = self.buffer.read(frames)

        # Ensure data has the right number of frames (in case buffer returns wrong size)
        if data.shape[0] != frames:
            if data.shape[0] > frames:
                data = data[:frames]
            else:
                # Pad with zeros
                pad = np.zeros((frames - data.shape[0], data.shape[1]), dtype=data.dtype)
                data = np.vstack([data, pad])

        # Handle channel count mismatch
        if data.shape[1] != outdata.shape[1]:
            if data.shape[1] == 1 and outdata.shape[1] > 1:
                # Mono to stereo: duplicate
                outdata[:] = np.repeat(data, outdata.shape[1], axis=1)
            elif data.shape[1] > 1 and outdata.shape[1] == 1:
                # Stereo to mono: mix down
                outdata[:, 0] = np.mean(data, axis=1)
            else:
                # Truncate or pad
                min_ch = min(data.shape[1], outdata.shape[1])
                outdata[:, :min_ch] = data[:, :min_ch]
                if min_ch < outdata.shape[1]:
                    outdata[:, min_ch:] = 0
        else:
            outdata[:] = data

    def _finished_callback(self):
        """Called when stream finishes."""
        self._running = False

    def write(self, data: np.ndarray) -> int:
        """Write audio block to buffer.

        Args:
            data: Audio data of shape (n_samples, channels) or (n_samples,)

        Returns:
            Number of samples written
        """
        return self.buffer.write(data)

    def write_block(self, data: np.ndarray) -> int:
        """Write exactly one block, handling size mismatch."""
        if data.shape[0] != self.block_size:
            # Resize if needed (should not happen in normal operation)
            if data.shape[0] > self.block_size:
                data = data[: self.block_size]
            else:
                # Pad
                pad = np.zeros((self.block_size - data.shape[0], data.shape[1]), dtype=data.dtype)
                data = np.vstack([data, pad])
        return self.buffer.write(data)

    def get_stats(self) -> dict:
        """Get output statistics."""
        stats = self.buffer.get_stats()
        stats["running"] = self._running
        stats["device"] = self.device.name
        stats["sample_rate"] = self.sample_rate
        stats["block_size"] = self.block_size
        if self._stream:
            stats["actual_latency"] = self._stream.latency
        return stats

    def set_underflow_callback(self, callback: Callable):
        """Set callback for buffer underflow."""
        self._underflow_callback = callback

    @property
    def running(self) -> bool:
        return self._running

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def list_audio_devices() -> dict:
    """List all audio devices categorized by type."""
    return {
        "input": list_output_devices(),  # Reuse the function that lists all with output
        "output": list_output_devices(),
    }


def print_device_list():
    """Print formatted device list."""
    print("Input Devices:")
    for dev in list_output_devices():  # This lists all, filter for input
        # Actually need to use input-specific function
        pass

    # Use input module functions
    from .input import get_default_input_device, get_default_output_device, list_input_devices

    print("Input Devices:")
    default_in = get_default_input_device()
    for dev in list_input_devices():
        marker = " *" if dev == default_in else ""
        print(f"  {dev}{marker}")

    print("\nOutput Devices:")
    default_out = get_default_output_device()
    for dev in list_output_devices():
        marker = " *" if dev == default_out else ""
        print(f"  {dev}{marker}")
