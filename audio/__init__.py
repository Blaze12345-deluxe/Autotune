# Audio I/O Package

"""Audio input/output handling for real-time processing."""

from .buffer import RingBuffer, DoubleBuffer, AudioBlockPool
from .input import (
    AudioInput,
    DeviceInfo,
    list_input_devices,
    list_output_devices,
    list_all_devices,
    get_default_input_device,
    get_default_output_device,
    find_device,
    validate_device,
)
from .output import AudioOutput
from .engine import AudioEngine, CallbackEngine, EngineStats

__all__ = [
    # Buffer
    'RingBuffer', 'DoubleBuffer', 'AudioBlockPool',
    
    # Input
    'AudioInput', 'DeviceInfo',
    'list_input_devices', 'list_output_devices', 'list_all_devices',
    'get_default_input_device', 'get_default_output_device',
    'find_device', 'validate_device',
    
    # Output
    'AudioOutput',
    
    # Engine
    'AudioEngine', 'CallbackEngine', 'EngineStats',
]

__version__ = '0.1.0'