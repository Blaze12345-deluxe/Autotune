# Audio Pipeline Specification

## Real-Time Constraints
- **Hard real-time**: Audio callback must complete in < 50% of block time
- **At 48kHz, 256 samples**: Block = 5.33ms, budget = ~2.6ms
- **No allocations** in callback path
- **No locks** in callback path
- **Deterministic** execution time

## Block Processing Flow

### Callback Signature (sounddevice)
```python
def audio_callback(indata, outdata, frames, time_info, status):
    # indata:  (frames, channels) float32, range [-1, 1]
    # outdata: (frames, channels) float32, to be filled
    # frames:  block_size (e.g., 256)
    # time_info: input/output latency, current time
    # status:  CallbackFlags (overflow, underflow, etc.)
```

### Processing Pipeline (per block)
```
1. Receive indata from PortAudio
       │
       ▼
2. Validate: check for NaN/Inf, clamp to [-1, 1]
       │
       ▼
3. Convert to mono if multi-channel input
       │
       ▼
4. Push to InputBuffer (lock-free ring buffer)
       │
       ▼
5. Pop from InputBuffer → processor.process(block, sr)
       │
       ▼
6. Processor returns processed block (same shape)
       │
       ▼
7. Push to OutputBuffer
       │
       ▼
8. Pop from OutputBuffer → outdata
       │
       ▼
9. Handle underrun (silence) / overrun (drop)
```

## Buffer Management

### Ring Buffer Design
```python
class RingBuffer:
    def __init__(self, capacity: int, channels: int = 1, dtype=np.float32):
        self.capacity = capacity  # Power of 2
        self.buffer = np.zeros((capacity, channels), dtype=dtype)
        self.write_idx = 0
        self.read_idx = 0
        self.overruns = 0
        self.underruns = 0
    
    def write(self, data: np.ndarray) -> int:
        """Returns samples written. Non-blocking."""
    
    def read(self, n_samples: int) -> np.ndarray:
        """Returns available data (zero-padded if underrun)."""
    
    @property
    def available(self) -> int: ...
    @property
    def free(self) -> int: ...
```

### Buffer Sizing
- **Input buffer**: 4-8 blocks (1024-2048 samples) - absorbs scheduling jitter
- **Output buffer**: 4-8 blocks - prevents underruns
- **Total buffering**: ~20-40ms additional latency

### Overrun/Underrun Handling
- **Input overrun**: Drop oldest samples, increment counter, log warning
- **Output underrun**: Output silence, increment counter, log warning
- **Statistics**: Report every 1000 blocks or on demand

## Audio Engine State Machine
```
┌─────────┐    start()    ┌──────────┐    run()    ┌──────────┐
│ CREATED │ ────────────▶ │ STARTING │ ───────────▶ │ RUNNING  │
└─────────┘               └──────────┘             └────┬─────┘
                                                         │
                              stop()                     │ interrupt
                              ◀──────────────────────────┘
                                                         ▼
                                                    ┌──────────┐
                                                    │ STOPPING │
                                                    └────┬─────┘
                                                         │
                                                         ▼
                                                    ┌─────────┐
                                                    │ STOPPED │
                                                    └─────────┘
```

## Latency Budget (48kHz, 256 samples)
| Component | Samples | Time (ms) |
|-----------|---------|-----------|
| Input device buffer | ~256 | 5.3 |
| Input ring buffer | ~512 | 10.7 |
| Pitch detection (lookahead) | ~512 | 10.7 |
| Pitch shifting (STFT frames) | ~1024 | 21.3 |
| Output ring buffer | ~512 | 10.7 |
| Output device buffer | ~256 | 5.3 |
| **Total** | **~3072** | **~64** |

**Optimization targets**: Reduce lookahead, smaller STFT frames, lower device buffers

## Sample Rate Handling
- Native: 48000 Hz (preferred)
- Supported: 44100, 48000, 88200, 96000
- Resampling: Not in callback; configure device to native rate
- Block size: Power of 2 (64, 128, 256, 512, 1024)

## Channel Handling
- **Input**: Mono (channel 0) for processing, passthrough other channels
- **Output**: Mono processed → duplicate to all output channels
- **Future**: Stereo processing, mid/side

## Status Reporting
```python
@dataclass
class EngineStats:
    blocks_processed: int
    input_overruns: int
    output_underruns: int
    avg_processing_ms: float
    max_processing_ms: float
    current_latency_ms: float
    cpu_percent: float
```
- Updated every block in callback (atomic counters)
- Read by main thread for display/logging

## Clean Shutdown Sequence
1. Receive SIGINT/SIGTERM
2. Set `engine.running = False` (atomic flag)
3. Wait for callback to finish current block
4. Stop input/output streams
5. Join any worker threads
6. Close PortAudio
7. Print final statistics
8. Exit