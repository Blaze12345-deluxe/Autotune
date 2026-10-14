# Test Configuration

"""Pytest configuration and shared fixtures."""

import numpy as np
import pytest


@pytest.fixture
def sample_rate():
    """Standard sample rate for tests."""
    return 48000


@pytest.fixture
def block_size():
    """Standard block size for tests."""
    return 256


@pytest.fixture
def sine_440(sample_rate, block_size):
    """Generate 440 Hz sine wave block."""
    t = np.arange(block_size) / sample_rate
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)


@pytest.fixture
def sine_220(sample_rate, block_size):
    """Generate 220 Hz sine wave block."""
    t = np.arange(block_size) / sample_rate
    return np.sin(2 * np.pi * 220 * t).astype(np.float32)


@pytest.fixture
def sine_880(sample_rate, block_size):
    """Generate 880 Hz sine wave block."""
    t = np.arange(block_size) / sample_rate
    return np.sin(2 * np.pi * 880 * t).astype(np.float32)


@pytest.fixture
def silence(block_size):
    """Generate silence block."""
    return np.zeros(block_size, dtype=np.float32)


@pytest.fixture
def white_noise(block_size):
    """Generate white noise block."""
    return np.random.randn(block_size).astype(np.float32) * 0.01


@pytest.fixture
def chirp_signal(sample_rate):
    """Generate frequency sweep for pitch tracking tests."""
    duration = 1.0
    t = np.arange(int(sample_rate * duration)) / sample_rate
    f0, f1 = 220, 880
    return np.sin(2 * np.pi * (f0 + (f1 - f0) * t) * t).astype(np.float32)


@pytest.fixture
def major_scale_notes():
    """C major scale notes (MIDI)."""
    return [60, 62, 64, 65, 67, 69, 71, 72]  # C4 to C5


# Test markers
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "audio_hardware: marks tests requiring audio hardware")
