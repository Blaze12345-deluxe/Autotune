# Processing Base

"""Base classes and interfaces for audio processors."""

from abc import ABC, abstractmethod

import numpy as np


class AudioProcessor(ABC):
    """Abstract base class for all real-time audio processors.

    All processors must implement the process() method for real-time
    block-based audio processing. The method must be real-time safe:
    no allocations, no locks, no blocking calls.
    """

    @abstractmethod
    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Process one audio block.

        Args:
            audio_block: Input audio of shape (n_samples, channels) or (n_samples,)
            sample_rate: Sample rate in Hz

        Returns:
            Processed audio of same shape as input
        """
        pass

    def reset(self) -> None:
        """Reset processor state.

        Called when stream starts/stops or parameters change.
        """
        pass

    @property
    def latency_samples(self) -> int:
        """Algorithmic latency in samples.

        Returns:
            Number of samples of delay introduced by processor
        """
        return 0

    @property
    def name(self) -> str:
        """Processor name for display."""
        return self.__class__.__name__


class ProcessorFactory:
    """Factory for creating processor instances."""

    _registry = {}

    @classmethod
    def register(cls, name: str, processor_class):
        """Register a processor class."""
        cls._registry[name] = processor_class

    @classmethod
    def create(cls, name: str, settings, sample_rate: int, block_size: int) -> AudioProcessor:
        """Create processor instance."""
        if name not in cls._registry:
            raise ValueError(f"Unknown processor: {name}. Available: {list(cls._registry.keys())}")
        return cls._registry[name](settings, sample_rate, block_size)

    @classmethod
    def available(cls) -> list:
        """Get list of available processors."""
        return list(cls._registry.keys())


class ProcessingChain:
    """Chain multiple processors in series."""

    def __init__(self, processors: list):
        self.processors = processors

    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Process through all processors in chain."""
        result = audio_block
        for processor in self.processors:
            result = processor.process(result, sample_rate)
        return result

    def reset(self):
        for processor in self.processors:
            processor.reset()

    @property
    def latency_samples(self) -> int:
        return sum(p.latency_samples for p in self.processors)

    @property
    def name(self) -> str:
        return " + ".join(p.name for p in self.processors)


class BypassProcessor(AudioProcessor):
    """Processor that passes audio through unchanged (for testing)."""

    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        return audio_block.copy()

    @property
    def name(self) -> str:
        return "Bypass"


class GainProcessor(AudioProcessor):
    """Simple gain processor."""

    def __init__(self, gain_db: float = 0.0):
        self.gain_db = gain_db
        self._gain_linear = 10 ** (gain_db / 20)

    def set_gain_db(self, gain_db: float):
        self.gain_db = gain_db
        self._gain_linear = 10 ** (gain_db / 20)

    def process(self, audio_block: np.ndarray, sample_rate: int) -> np.ndarray:
        return audio_block * self._gain_linear

    @property
    def name(self) -> str:
        return f"Gain({self.gain_db:.1f}dB)"
