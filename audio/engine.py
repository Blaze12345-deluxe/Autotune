# Audio Engine

"""Main audio engine coordinating input, processing, and output."""

import signal
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

import numpy as np

from config.defaults import Settings
from processing.base import AudioProcessor

from .input import AudioInput
from .output import AudioOutput


@dataclass
class EngineStats:
    """Engine performance statistics."""

    blocks_processed: int = 0
    input_overruns: int = 0
    output_underruns: int = 0
    processing_time_ms: float = 0.0
    max_processing_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0
    total_callbacks: int = 0
    start_time: float = 0.0

    def update_processing_time(self, elapsed_ms: float):
        self.blocks_processed += 1
        self.processing_time_ms = elapsed_ms
        self.max_processing_time_ms = max(self.max_processing_time_ms, elapsed_ms)
        # Running average
        n = self.blocks_processed
        self.avg_processing_time_ms = ((n - 1) * self.avg_processing_time_ms + elapsed_ms) / n

    def get_uptime(self) -> float:
        return time.time() - self.start_time if self.start_time > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "blocks_processed": self.blocks_processed,
            "input_overruns": self.input_overruns,
            "output_underruns": self.output_underruns,
            "processing_time_ms": self.processing_time_ms,
            "max_processing_time_ms": self.max_processing_time_ms,
            "avg_processing_time_ms": self.avg_processing_time_ms,
            "uptime_sec": self.get_uptime(),
            "callbacks_per_sec": (
                self.blocks_processed / self.get_uptime() if self.get_uptime() > 0 else 0
            ),
        }


class AudioEngine:
    """Main audio engine managing the real-time processing pipeline.

    Pipeline:
    Input Device -> Ring Buffer -> Processor -> Ring Buffer -> Output Device
    """

    def __init__(
        self,
        processor: AudioProcessor,
        settings: Settings,
        input_device: Optional = None,
        output_device: Optional = None,
    ):
        """Initialize audio engine.

        Args:
            processor: AudioProcessor implementation
            settings: Global settings
            input_device: Optional input device override
            output_device: Optional output device override
        """
        self.processor = processor
        self.settings = settings

        # Audio settings
        audio = settings.audio
        self.sample_rate = audio.sample_rate
        self.block_size = audio.block_size
        self.input_channels = audio.channels
        self.output_channels = 2  # Stereo output

        # Initialize I/O
        self.input = AudioInput(
            device=input_device,
            sample_rate=self.sample_rate,
            block_size=self.block_size,
            channels=self.input_channels,
            latency=audio.input_latency,
            buffer_size=8192,  # 4-8 blocks
        )

        self.output = AudioOutput(
            device=output_device,
            sample_rate=self.sample_rate,
            block_size=self.block_size,
            channels=self.output_channels,
            latency=audio.output_latency,
            buffer_size=8192,
        )

        # State
        self._running = False
        self._stop_event = threading.Event()
        self._stats = EngineStats()

        # Callbacks
        self._error_callback: Callable[[Exception], None] | None = None

        # Processing thread
        self._processing_thread: Optional[threading.Thread] = None

        # Signal handling
        self._signal_handlers_installed = False

    def start(self):
        """Start audio engine."""
        if self._running:
            return

        # Reset processor
        self.processor.reset()

        # Install signal handlers for clean shutdown
        if not self._signal_handlers_installed:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self._signal_handlers_installed = True

        # Start I/O
        self.output.start()
        self.input.start()

        # Prime output buffer with silence
        silence = np.zeros((self.block_size, self.output_channels), dtype=np.float32)
        for _ in range(4):  # Pre-fill with a few blocks
            self.output.write(silence)

        self._running = True
        self._stop_event.clear()
        self._stats.start_time = time.time()

        # Start processing thread
        self._processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._processing_thread.start()

    def stop(self):
        """Stop audio engine."""
        if not self._running:
            return

        self._stop_event.set()
        self._running = False

        # Wait for processing thread to finish
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=2.0)

        # Stop I/O
        self.input.stop()
        self.output.stop()

    def run(self, timeout: float | None = None):
        """Run engine until stopped or timeout.

        This method blocks and processes audio in the main thread.
        For callback-based operation, use run_callback_mode().
        """
        if not self._running:
            self.start()

        try:
            if timeout:
                self._stop_event.wait(timeout)
            else:
                self._stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def run_callback_mode(self):
        """Run in callback mode (PortAudio callbacks handle processing).

        This is the preferred mode for lowest latency.
        The engine's internal callback processes audio.
        """
        if not self._running:
            self.start()

        # In callback mode, the PortAudio callbacks do the work
        # We just wait for stop signal
        try:
            self._stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self._stop_event.set()

    def process_block(self, input_block: np.ndarray) -> np.ndarray:
        """Process a single audio block.

        This is called from the audio callback (real-time context).

        Args:
            input_block: Input audio of shape (block_size, input_channels)

        Returns:
            Output audio of shape (block_size, output_channels)
        """
        start = time.perf_counter()

        try:
            # Convert to mono if needed
            if input_block.shape[1] > 1:
                mono = np.mean(input_block, axis=1, keepdims=True)
            else:
                mono = input_block

            # Process through processor
            processed = self.processor.process(mono, self.sample_rate)

            # Ensure correct output shape
            if processed.ndim == 1:
                processed = processed[:, np.newaxis]

            # Convert to output channels (stereo)
            if processed.shape[1] == 1 and self.output_channels > 1:
                output = np.repeat(processed, self.output_channels, axis=1)
            elif processed.shape[1] >= self.output_channels:
                output = processed[:, : self.output_channels]
            else:
                # Pad
                pad = np.zeros(
                    (processed.shape[0], self.output_channels - processed.shape[1]),
                    dtype=processed.dtype,
                )
                output = np.hstack([processed, pad])

        except Exception as e:
            # On error, pass through dry signal
            if self._error_callback:
                self._error_callback(e)
            output = input_block
            if output.shape[1] != self.output_channels:
                if output.shape[1] == 1:
                    output = np.repeat(output, self.output_channels, axis=1)
                else:
                    output = output[:, : self.output_channels]

        elapsed = (time.perf_counter() - start) * 1000
        self._stats.update_processing_time(elapsed)
        self._stats.total_callbacks += 1

        return output

    def _processing_loop(self):
        """Processing loop that runs in a separate thread.
        
        Continuously reads from input buffer, processes through the processor,
        and writes to output buffer.
        """
        while self._running and not self._stop_event.is_set():
            try:
                # Read block from input buffer
                input_block = self.input.read_block()
                
                # Process the block
                output_block = self.process_block(input_block)
                
                # Write to output buffer
                self.output.write_block(output_block)
                
            except Exception as e:
                if self._error_callback:
                    self._error_callback(e)
                # Small sleep to prevent busy loop on error
                time.sleep(0.001)

    def get_stats(self) -> dict:
        """Get combined engine statistics."""
        stats = self._stats.to_dict()
        stats["input"] = self.input.get_stats()
        stats["output"] = self.output.get_stats()
        stats["processor"] = self.processor.name
        stats["processor_latency_samples"] = self.processor.latency_samples
        stats["processor_latency_ms"] = self.processor.latency_samples / self.sample_rate * 1000
        return stats

    def set_error_callback(self, callback: Callable[[Exception], None]):
        """Set callback for processing errors."""
        self._error_callback = callback

    @property
    def running(self) -> bool:
        return self._running

    @property
    def stats(self) -> EngineStats:
        return self._stats

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class CallbackEngine:
    """Alternative engine using PortAudio callback for processing.

    This version puts the processing directly in the PortAudio callback
    for minimal latency, but with stricter real-time constraints.
    """

    def __init__(
        self,
        processor: AudioProcessor,
        settings: Settings,
        input_device: Optional = None,
        output_device: Optional = None,
    ):
        self.processor = processor
        self.settings = settings

        audio = settings.audio
        self.sample_rate = audio.sample_rate
        self.block_size = audio.block_size
        self.input_channels = audio.channels
        self.output_channels = 2

        # Use combined duplex stream for lowest latency
        self._stream = None
        self._running = False
        self._stop_event = threading.Event()
        self._stats = EngineStats()

        # Get devices
        from .input import get_default_input_device, get_default_output_device, validate_device

        in_dev = validate_device(input_device or get_default_input_device(), True)
        out_dev = validate_device(output_device or get_default_output_device(), False)

        self.input_device = in_dev
        self.output_device = out_dev

    def start(self):
        """Start duplex stream."""
        if self._running:
            return

        self.processor.reset()

        self._stream = sd.Stream(
            device=(self.input_device.index, self.output_device.index),
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=(self.input_channels, self.output_channels),
            dtype=np.float32,
            latency=(
                self.input_device.default_low_input_latency,
                self.output_device.default_low_output_latency,
            ),
            callback=self._duplex_callback,
            finished_callback=self._finished_callback,
        )
        self._stream.start()
        self._running = True
        self._stop_event.clear()
        self._stats.start_time = time.time()

    def stop(self):
        if not self._running:
            return
        self._stop_event.set()
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False

    def run(self, timeout: float | None = None):
        self.start()
        try:
            if timeout:
                self._stop_event.wait(timeout)
            else:
                self._stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _duplex_callback(self, indata, outdata, frames, time_info, status):
        """Duplex callback - processes and passes through in one call."""
        start = time.perf_counter()

        if status.input_overflow:
            pass  # Counted elsewhere
        if status.output_underflow:
            pass

        try:
            # Convert to mono
            if indata.shape[1] > 1:
                mono = np.mean(indata, axis=1, keepdims=True)
            else:
                mono = indata

            # Process
            processed = self.processor.process(mono, self.sample_rate)

            # Handle output shape
            if processed.ndim == 1:
                processed = processed[:, np.newaxis]

            if processed.shape[1] == 1 and outdata.shape[1] > 1:
                outdata[:] = np.repeat(processed, outdata.shape[1], axis=1)
            elif processed.shape[1] >= outdata.shape[1]:
                outdata[:] = processed[:, : outdata.shape[1]]
            else:
                outdata[:, : processed.shape[1]] = processed
                outdata[:, processed.shape[1] :] = 0

        except Exception:
            # Pass through on error
            outdata[:] = (
                indata[:, : outdata.shape[1]] if indata.shape[1] >= outdata.shape[1] else indata
            )

        elapsed = (time.perf_counter() - start) * 1000
        self._stats.update_processing_time(elapsed)
        self._stats.total_callbacks += 1

    def _finished_callback(self):
        self._running = False

    def get_stats(self) -> dict:
        return self._stats.to_dict()

    @property
    def running(self) -> bool:
        return self._running


# Import sounddevice here to avoid circular import
import sounddevice as sd
