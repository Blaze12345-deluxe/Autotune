# Processing Package

"""Signal processing modules for Auto-Tune & Harmoniser."""

from .base import AudioProcessor, ProcessorFactory, ProcessingChain, BypassProcessor, GainProcessor
from .pitch_detector import PitchDetector, PitchResult, YINPitchDetector
from .pitch_shifter import PitchShifter, SimplePitchShifter, PhaseVocoderState
from .autotune import AutoTuneProcessor, CorrectionSmoother, create_autotune_processor
from .harmoniser import HarmoniserProcessor, VoiceState, create_harmoniser_processor

__all__ = [
    # Base
    'AudioProcessor', 'ProcessorFactory', 'ProcessingChain', 
    'BypassProcessor', 'GainProcessor',
    
    # Pitch Detection
    'PitchDetector', 'PitchResult', 'YINPitchDetector',
    
    # Pitch Shifting
    'PitchShifter', 'SimplePitchShifter', 'PhaseVocoderState',
    
    # Processors
    'AutoTuneProcessor', 'CorrectionSmoother', 'create_autotune_processor',
    'HarmoniserProcessor', 'VoiceState', 'create_harmoniser_processor',
]

__version__ = '0.1.0'