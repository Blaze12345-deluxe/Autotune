# Development Roadmap

## Phase 1: Audio Foundation (Weeks 1-2)
**Goal**: Capture microphone input, play through speakers, clean shutdown

### Tasks
- [ ] Project structure setup (folders, `__init__.py`, `requirements.txt`)
- [ ] `config/defaults.py` - Default settings dataclasses
- [ ] `audio/buffer.py` - Lock-free ring buffer implementation
- [ ] `audio/input.py` - Device enumeration, input stream
- [ ] `audio/output.py` - Device enumeration, output stream
- [ ] `audio/engine.py` - AudioEngine with callback wiring
- [ ] `auto-tune.py` - CLI with `--list-devices`, basic args
- [ ] Pass-through mode (no processing) working end-to-end
- [ ] Clean Ctrl+C handling, resource cleanup
- [ ] Buffer overrun/underrun statistics

### Deliverables
```bash
python auto-tune.py --list-devices
python auto-tune.py          # Pass-through (no mode selected yet)
```

### Acceptance Criteria
- Runs for 10+ minutes without xruns
- Latency < 50ms end-to-end
- Clean shutdown on SIGINT
- Device selection works

---

## Phase 2: Pitch Detection (Weeks 3-4)
**Goal**: Accurate, real-time fundamental frequency estimation

### Tasks
- [ ] `music/notes.py` - Note/frequency/MIDI conversions
- [ ] `music/scales.py` - Scale definitions, quantization
- [ ] `processing/pitch_detector.py` - YIN implementation
- [ ] Unit tests with synthetic signals (sine, chirp, noise)
- [ ] Integration with AudioEngine (detector runs in callback)
- [ ] Confidence gating, silence detection
- [ ] Visualization script for debugging pitch tracks

### Deliverables
```bash
python -m tests.test_pitch_detector    # Unit tests pass
python scripts/visualize_pitch.py      # Real-time pitch display
```

### Acceptance Criteria
- ±2 Hz accuracy on sine waves 80-1000 Hz
- Confidence > 0.9 on clean vowels
- Silence/noise correctly rejected (confidence < 0.3)
- < 1ms CPU per frame on modern CPU

---

## Phase 3: Auto-Tune (Weeks 5-7)
**Goal**: Working pitch correction with musical quantization

### Tasks
- [ ] `processing/pitch_shifter.py` - Phase vocoder implementation
- [ ] `music/chords.py` - Chord definitions (for future)
- [ ] `music/harmony.py` - Harmony rules (for future)
- [ ] `processing/autotune.py` - AutoTuneProcessor
- [ ] Correction speed smoothing
- [ ] Threshold gating
- [ ] Formant preservation
- [ ] Wet/dry mix
- [ ] CLI integration: `--autotune`, `--key`, `--scale`, `--correction-speed`, `--threshold`
- [ ] Comprehensive unit tests

### Deliverables
```bash
python auto-tune.py --autotune --key C --scale major
python auto-tune.py --autotune --key C --scale major --correction-speed 0.9
```

### Acceptance Criteria
- Corrects flat/sharp notes to nearest scale tone
- "T-Pain" mode (fast correction) sounds robotic
- "Natural" mode (slow correction) transparent
- No artifacts on silence/unvoiced
- CPU < 50% of block budget

---

## Phase 4: Harmoniser (Weeks 8-10)
**Goal**: Real-time harmony generation

### Tasks
- [ ] `processing/harmoniser.py` - HarmoniserProcessor
- [ ] VoiceManager for parallel pitch shifting
- [ ] Interval-based harmony (fixed intervals)
- [ ] Scale-degree harmony (diatonic)
- [ ] Chord-based harmony
- [ ] Voice volume balancing
- [ ] Anti-clipping mixer (soft limiting)
- [ ] Harmony smoothing (voice leading)
- [ ] CLI integration: `--harmonise`, `--intervals`, `--voice-volumes`, `--chord-mode`
- [ ] Presets (subtle, backup, choir, power chord)

### Deliverables
```bash
python auto-tune.py --harmonise --key C --scale major --intervals 4,7
python auto-tune.py --harmonise --key C --scale major --chord-mode scale
```

### Acceptance Criteria
- Generates 1-3 harmony voices in real-time
- Harmonies stay in key/scale
- No clipping with multiple voices
- Smooth transitions between notes
- Lead voice preserved by default

---

## Phase 5: Configuration & Polish (Weeks 11-12)
**Goal**: Complete CLI, settings persistence, documentation

### Tasks
- [ ] Complete all CLI flags per spec
- [ ] `config/defaults.py` - All settings with validation
- [ ] Settings file support (JSON/YAML) - optional
- [ ] Logging configuration (`-v`, `-vv`, `-vvv`)
- [ ] `--version` flag
- [ ] README.md with usage examples
- [ ] Performance profiling and optimization
- [ ] Cross-platform testing (Linux, macOS, Windows)

### Deliverables
```bash
python auto-tune.py --help
python auto-tune.py --autotune --key G --scale minor --correction-speed 0.3
```

### Acceptance Criteria
- All documented CLI options work
- Help text is clear and complete
- Runs on Linux/macOS/Windows
- No memory leaks in long runs

---

## Phase 6: Quality & Performance (Weeks 13-14)
**Goal**: Production-ready quality

### Tasks
- [ ] Latency measurement and optimization
- [ ] Audio quality evaluation (PESQ, subjective)
- [ ] Stress testing (high CPU load, buffer pressure)
- [ ] Edge case handling (device disconnect, sample rate change)
- [ ] Memory profiling, leak fixes
- [ ] Pitch shifter quality improvements
- [ ] Formant preservation tuning
- [ ] Documentation of known limitations

### Acceptance Criteria
- Latency < 30ms on typical hardware
- No audible artifacts on clean vocals
- Handles 30+ minute sessions
- Graceful degradation under load

---

## Phase 7: Future Expansion (Post-v1.0)
**Goal**: Platform for advanced features

### Potential Features
- [ ] GUI (Tkinter, Qt, or web-based)
- [ ] MIDI input for harmony control
- [ ] Chord progression tracking
- [ ] Preset management
- [ ] Effects chain (reverb, delay, EQ, compression)
- [ ] Recording to WAV
- [ ] VST/AU plugin wrapper
- [ ] Deep learning pitch detection (CREPE)
- [ ] Multi-channel support (stereo, surround)
- [ ] Network audio (Jack, PipeWire, ASIO)

---

## Milestone Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 1 | 2 weeks | Audio I/O working |
| 2 | 2 weeks | Pitch detection working |
| 3 | 3 weeks | Auto-Tune working |
| 4 | 3 weeks | Harmoniser working |
| 5 | 2 weeks | Full CLI, docs |
| 6 | 2 weeks | Production quality |
| **Total** | **~14 weeks** | **v1.0 Release** |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Phase vocoder quality insufficient | High | Prototype early; fallback to Rubber Band |
| Latency too high for live use | High | Profile early; optimize buffer sizes |
| YIN fails on breathy vocals | Medium | Add PYIN/CREPE as alternative |
| PortAudio device issues on Windows | Medium | Test on all platforms early; provide troubleshooting |
| Real-time thread crashes | Critical | Extensive callback testing; watchdog timer |

---

## Definition of Done (Per Phase)
- All unit tests pass (`pytest -x`)
- Integration tests pass
- No mypy errors (`mypy --strict`)
- Code formatted (`black .`)
- No ruff violations (`ruff check .`)
- Documentation updated
- Demoed to stakeholder (you)