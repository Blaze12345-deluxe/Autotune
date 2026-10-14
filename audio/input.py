# Audio Input

"""Microphone input handling and device management."""

from dataclasses import dataclass
from typing import Any

import numpy as np
import sounddevice as sd

from .buffer import RingBuffer


@dataclass
class DeviceInfo:
    """Audio device information."""

    index: int
    name: str
    host_api: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    default_low_input_latency: float
    default_low_output_latency: float
    default_high_input_latency: float
    default_high_output_latency: float

    @classmethod
    def from_sd_dict(cls, data: dict[str, Any], index: int) -> "DeviceInfo":
        """Create from sounddevice device dict."""
        return cls(
            index=index,
            name=data["name"],
            host_api=sd.query_hostapis(data["hostapi"])["name"],
            max_input_channels=data["max_input_channels"],
            max_output_channels=data["max_output_channels"],
            default_sample_rate=data["default_samplerate"],
            default_low_input_latency=data["default_low_input_latency"],
            default_low_output_latency=data["default_low_output_latency"],
            default_high_input_latency=data["default_high_input_latency"],
            default_high_output_latency=data["default_high_output_latency"],
        )

    def supports_input(self) -> bool:
        return self.max_input_channels > 0

    def supports_output(self) -> bool:
        return self.max_output_channels > 0

    def __str__(self) -> str:
        return (
            f"{self.index}: {self.name} "
            f"({self.max_input_channels} in, {self.max_output_channels} out) "
            f"@ {self.default_sample_rate:.0f}Hz"
        )


def list_input_devices() -> list[DeviceInfo]:
    """List all available input devices."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append(DeviceInfo.from_sd_dict(dev, i))
    return devices


def list_output_devices() -> list[DeviceInfo]:
    """List all available output devices."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0:
            devices.append(DeviceInfo.from_sd_dict(dev, i))
    return devices


def list_all_devices() -> list[DeviceInfo]:
    """List all audio devices."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        devices.append(DeviceInfo.from_sd_dict(dev, i))
    return devices


def get_default_input_device() -> DeviceInfo | None:
    """Get default input device."""
    try:
        idx = sd.default.device[0]
        if idx >= 0:
            return DeviceInfo.from_sd_dict(sd.query_devices(idx), idx)
    except Exception:
        pass
    # Fallback: first input device
    inputs = list_input_devices()
    return inputs[0] if inputs else None


def get_default_output_device() -> DeviceInfo | None:
    """Get default output device."""
    try:
        idx = sd.default.device[1]
        if idx >= 0:
            return DeviceInfo.from_sd_dict(sd.query_devices(idx), idx)
    except Exception:
        pass
    # Fallback: first output device
    outputs = list_output_devices()
    return outputs[0] if outputs else None


def find_device(
    query: str, input_only: bool = False, output_only: bool = False
) -> DeviceInfo | None:
    """Find device by index or name substring.

    Args:
        query: Device index (int) or name substring (str)
        input_only: Only search input devices
        output_only: Only search output devices

    Returns:
        DeviceInfo or None if not found
    """
    # Try as index
    try:
        idx = int(query)
        dev = sd.query_devices(idx)
        info = DeviceInfo.from_sd_dict(dev, idx)
        if input_only and not info.supports_input():
            return None
        if output_only and not info.supports_output():
            return None
        return info
    except (ValueError, IndexError):
        pass

    # Try as name substring (case insensitive)
    query_lower = query.lower()
    devices = list_all_devices()

    for dev in devices:
        if query_lower in dev.name.lower():
            if input_only and not dev.supports_input():
                continue
            if output_only and not dev.supports_output():
                continue
            return dev

    return None


def validate_device(device: DeviceInfo | None, input_required: bool = True) -> DeviceInfo:
    """Validate and return device, or raise error."""
    if device is None:
        if input_required:
            raise ValueError("No input device found")
        else:
            raise ValueError("No output device found")

    if input_required and not device.supports_input():
        raise ValueError(f"Device {device.name} does not support input")

    if not input_required and not device.supports_output():
        raise ValueError(f"Device {device.name} does not support output")

    return device


class AudioInput:
    """Microphone input stream manager."""

    def __init__(
        self,
        device: DeviceInfo | None = None,
        sample_rate: int = 48000,
        block_size: int = 256,
        channels: int = 1,
        latency: str = "low",
        dtype: np.dtype = np.float32,
        buffer_size: int = 4096,
    ):
        """Initialize audio input.

        Args:
            device: Input device (None = default)
            sample_rate: Sample rate in Hz
            block_size: Block size in samples
            channels: Number of input channels
            latency: 'low', 'high', or specific latency in seconds
            dtype: Data type
            buffer_size: Internal ring buffer size (power of 2)
        """
        self.device = device or get_default_input_device()
        self.device = validate_device(self.device, input_required=True)

        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels
        self.dtype = dtype

        # Configure latency
        if latency == "low":
            self.latency = self.device.default_low_input_latency
        elif latency == "high":
            self.latency = self.device.default_high_input_latency
        else:
            self.latency = float(latency)

        # Ring buffer for thread-safe transfer
        self.buffer = RingBuffer(buffer_size, channels, dtype)

        # Stream
        self._stream: sd.InputStream | None = None
        self._running = False

        # Callbacks
        self._overflow_callback = None

    def start(self):
        """Start the input stream."""
        if self._running:
            return

        self._stream = sd.InputStream(
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
        """Stop the input stream."""
        if not self._running:
            return

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False

    def _callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags):
        """Audio callback - runs on PortAudio thread."""
        if status.input_overflow:
            self.buffer.overruns += 1
            if self._overflow_callback:
                self._overflow_callback()

        # Write to ring buffer (non-blocking)
        self.buffer.write(indata)

    def _finished_callback(self):
        """Called when stream finishes."""
        self._running = False

    def read(self, n_samples: int) -> np.ndarray:
        """Read audio block from buffer."""
        return self.buffer.read(n_samples)

    def read_block(self) -> np.ndarray:
        """Read exactly one block."""
        return self.buffer.read(self.block_size)

    def get_stats(self) -> dict:
        """Get input statistics."""
        stats = self.buffer.get_stats()
        stats["running"] = self._running
        stats["device"] = self.device.name
        stats["sample_rate"] = self.sample_rate
        stats["block_size"] = self.block_size
        if self._stream:
            stats["actual_latency"] = self._stream.latency
        return stats

    def set_overflow_callback(self, callback):
        """Set callback for buffer overflow."""
        self._overflow_callback = callback

    @property
    def running(self) -> bool:
        return self._running

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
