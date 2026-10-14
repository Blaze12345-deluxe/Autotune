# Audio Buffer

"""Lock-free ring buffers for real-time audio processing."""


import numpy as np


class RingBuffer:
    """Lock-free single-producer/single-consumer ring buffer.

    Designed for real-time audio: no allocations, no locks in hot path.
    Uses power-of-2 capacity for fast modulo operations.
    """

    def __init__(
        self,
        capacity: int,
        channels: int = 1,
        dtype: np.dtype = np.float32,
    ):
        """Initialize ring buffer.

        Args:
            capacity: Buffer capacity in samples (must be power of 2)
            channels: Number of audio channels
            dtype: Data type (default float32)
        """
        if capacity & (capacity - 1) != 0:
            raise ValueError("Capacity must be a power of 2")

        self.capacity = capacity
        self.channels = channels
        self.dtype = dtype
        self.mask = capacity - 1

        self._buffer = np.zeros((capacity, channels), dtype=dtype)
        self._write_idx = 0
        self._read_idx = 0

        # Statistics
        self.overruns = 0
        self.underruns = 0
        self._max_overrun = 0
        self._max_underrun = 0

    @property
    def available(self) -> int:
        """Number of samples available to read."""
        return (self._write_idx - self._read_idx) & self.mask

    @property
    def free(self) -> int:
        """Number of free samples for writing."""
        return self.capacity - self.available - 1  # -1 to distinguish full/empty

    @property
    def is_empty(self) -> bool:
        return self.available == 0

    @property
    def is_full(self) -> bool:
        return self.free == 0

    def write(self, data: np.ndarray) -> int:
        """Write audio data to buffer.

        Non-blocking: writes as much as possible, drops rest on overrun.

        Args:
            data: Audio data array of shape (n_samples, channels) or (n_samples,)

        Returns:
            Number of samples written
        """
        if data.ndim == 1:
            data = data[:, np.newaxis]

        n_samples = data.shape[0]
        if n_samples == 0:
            return 0

        free = self.free

        if n_samples > free:
            # Overrun: drop oldest samples
            self.overruns += 1
            overrun_amount = n_samples - free
            if overrun_amount > self._max_overrun:
                self._max_overrun = overrun_amount
            n_samples = free
            data = data[:n_samples]

        if n_samples == 0:
            return 0

        # Write in one or two chunks (wrap around)
        write_pos = self._write_idx & self.mask
        first_chunk = min(n_samples, self.capacity - write_pos)

        self._buffer[write_pos : write_pos + first_chunk] = data[:first_chunk]

        if first_chunk < n_samples:
            # Wrap around
            second_chunk = n_samples - first_chunk
            self._buffer[0:second_chunk] = data[first_chunk:]

        self._write_idx = (self._write_idx + n_samples) & self.mask
        return n_samples

    def read(self, n_samples: int) -> np.ndarray:
        """Read audio data from buffer.

        Non-blocking: returns available data, zero-pads on underrun.

        Args:
            n_samples: Number of samples to read

        Returns:
            Audio data array of shape (n_samples, channels)
        """
        if n_samples == 0:
            return np.zeros((0, self.channels), dtype=self.dtype)

        available = self.available

        if n_samples > available:
            # Underrun: pad with zeros
            self.underruns += 1
            underrun_amount = n_samples - available
            if underrun_amount > self._max_underrun:
                self._max_underrun = underrun_amount

        # Read available data
        read_pos = self._read_idx & self.mask
        first_chunk = min(available, self.capacity - read_pos)

        result = np.zeros((n_samples, self.channels), dtype=self.dtype)

        if available > 0:
            result[:first_chunk] = self._buffer[read_pos : read_pos + first_chunk]

            if first_chunk < available:
                second_chunk = available - first_chunk
                result[first_chunk : first_chunk + second_chunk] = self._buffer[0:second_chunk]

        self._read_idx = (self._read_idx + n_samples) & self.mask
        return result

    def peek(self, n_samples: int) -> np.ndarray:
        """Read without advancing read pointer (for monitoring)."""
        available = self.available
        n_samples = min(n_samples, available)

        if n_samples == 0:
            return np.zeros((0, self.channels), dtype=self.dtype)

        read_pos = self._read_idx & self.mask
        first_chunk = min(n_samples, self.capacity - read_pos)

        result = np.zeros((n_samples, self.channels), dtype=self.dtype)
        result[:first_chunk] = self._buffer[read_pos : read_pos + first_chunk]

        if first_chunk < n_samples:
            result[first_chunk:] = self._buffer[0 : n_samples - first_chunk]

        return result

    def clear(self):
        """Clear buffer and reset indices."""
        self._write_idx = 0
        self._read_idx = 0
        self.overruns = 0
        self.underruns = 0

    def get_stats(self) -> dict:
        """Get buffer statistics."""
        return {
            "capacity": self.capacity,
            "available": self.available,
            "free": self.free,
            "overruns": self.overruns,
            "underruns": self.underruns,
            "max_overrun": self._max_overrun,
            "max_underrun": self._max_underrun,
            "utilization": self.available / self.capacity,
        }

    def reset_stats(self):
        """Reset statistics counters."""
        self.overruns = 0
        self.underruns = 0
        self._max_overrun = 0
        self._max_underrun = 0


class DoubleBuffer:
    """Double buffer for lock-free producer/consumer with swap.

    Used when producer and consumer need to exchange entire buffers atomically.
    """

    def __init__(self, block_size: int, channels: int = 1, dtype: np.dtype = np.float32):
        self.block_size = block_size
        self.channels = channels
        self.dtype = dtype

        self._buffers = [
            np.zeros((block_size, channels), dtype=dtype),
            np.zeros((block_size, channels), dtype=dtype),
        ]
        self._write_buffer = 0
        self._read_buffer = 1
        self._write_ready = False

    @property
    def write_buffer(self) -> np.ndarray:
        """Get buffer for writing."""
        return self._buffers[self._write_buffer]

    @property
    def read_buffer(self) -> np.ndarray:
        """Get buffer for reading."""
        return self._buffers[self._read_buffer]

    def swap(self):
        """Atomically swap read/write buffers."""
        self._write_buffer, self._read_buffer = self._read_buffer, self._write_buffer
        self._write_ready = True

    def is_ready(self) -> bool:
        """Check if new data is available for reading."""
        return self._write_ready

    def mark_consumed(self):
        """Mark current read buffer as consumed."""
        self._write_ready = False


class AudioBlockPool:
    """Pre-allocated pool of audio blocks to avoid allocations in callback."""

    def __init__(
        self, block_size: int, channels: int, pool_size: int = 8, dtype: np.dtype = np.float32
    ):
        self.block_size = block_size
        self.channels = channels
        self.dtype = dtype

        self._pool = [np.zeros((block_size, channels), dtype=dtype) for _ in range(pool_size)]
        self._available = list(range(pool_size))
        self._in_use = set()

    def acquire(self) -> np.ndarray:
        """Get a block from the pool."""
        if not self._available:
            # Pool exhausted - allocate new (should not happen in steady state)
            return np.zeros((self.block_size, self.channels), dtype=self.dtype)

        idx = self._available.pop()
        self._in_use.add(idx)
        return self._pool[idx]

    def release(self, block: np.ndarray):
        """Return a block to the pool."""
        # Find block index
        try:
            idx = self._pool.index(block)
            if idx in self._in_use:
                self._in_use.remove(idx)
                self._available.append(idx)
        except ValueError:
            pass  # Block not from this pool

    def clear(self):
        """Clear all blocks (set to zero)."""
        for block in self._pool:
            block.fill(0)
