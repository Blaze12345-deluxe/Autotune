# Troubleshooting Guide

## Common Issues

### Audio Issues

#### No Sound Output
**Symptoms**: Program runs but no audio heard

**Solutions**:
1. Check output device selection:
   ```bash
   python auto-tune.py --list-devices
   python auto-tune.py --autotune --output-device <index_or_name>
   ```
2. Verify system volume not muted
3. Check correct output device in OS sound settings
4. Try default device explicitly: `--output-device 0`

#### No Input / Microphone Not Working
**Symptoms**: No pitch detection, silence passes through

**Solutions**:
1. Check input device:
   ```bash
   python auto-tune.py --list-devices
   python auto-tune.py --autotune --input-device <index_or_name>
   ```
2. Verify microphone permissions (macOS: System Preferences → Security → Microphone)
3. Check input gain in OS sound settings
4. Test with `arecord` (Linux) or Voice Memos (macOS)

#### Audio Glitches (Clicks, Pops, Dropouts)
**Symptoms**: Audible artifacts, buffer overrun/underrun warnings

**Solutions**:
1. Increase block size:
   ```bash
   python auto-tune.py --autotune --block-size 512
   # or
   python auto-tune.py --autotune --block-size 1024
   ```
2. Close other audio applications
3. Increase buffer sizes in audio engine (code modification)
4. Use lower sample rate: `--sample-rate 44100`
5. On Linux: Use JACK with realtime priority
6. On Windows: Use ASIO driver if available

#### High Latency
**Symptoms**: Noticeable delay between singing and hearing output

**Solutions**:
1. Decrease block size:
   ```bash
   python auto-tune.py --autotune --block-size 128
   # or
   python auto-tune.py --autotune --block-size 64
   ```
2. Increase sample rate: `--sample-rate 96000` (if device supports)
3. Use low-latency audio backend:
   - Linux: JACK (`pip install jack-client`)
   - Windows: ASIO (via sounddevice ASIO backend)
   - macOS: Core Audio (default, already low latency)
4. Reduce algorithmic latency (smaller FFT in pitch shifter)

### Pitch Detection Issues

#### Pitch Detection Unreliable / Jumping
**Symptoms**: Detected pitch fluctuates, wrong notes corrected

**Solutions**:
1. Improve signal quality:
   - Use directional microphone close to mouth
   - Reduce background noise
   - Avoid room reverb (use close-mic technique)
2. Check input gain:
   - Too low: poor signal-to-noise ratio
   - Too high: clipping distorts pitch detection
   - Aim for -12dB to -6dB peak levels
3. Adjust detector parameters (code):
   - Increase `frame_size` for better frequency resolution
   - Adjust `threshold` (0.05-0.2)
   - Narrow `min_freq`/`max_freq` to vocal range

#### Octave Errors
**Symptoms**: Pitch detected at double/half frequency

**Solutions**:
1. Narrow frequency range:
   ```python
   # In config/defaults.py or code
   PitchDetectorSettings(min_freq=80, max_freq=1000)
   ```
2. Use confidence gating (already implemented)
3. Future: PYIN probabilistic tracker

#### No Pitch Detected on Quiet Passages
**Symptoms**: Silence between phrases causes artifacts

**Solutions**:
1. This is expected behavior - silence correctly returns `voiced=False`
2. Adjust RMS gate threshold in `PitchDetector`
3. Ensure `correction_threshold` in Auto-Tune prevents correction on silence

### Auto-Tune Issues

#### Correction Sounds Unnatural / Robotic
**Symptoms**: Even at low speed, correction sounds artificial

**Solutions**:
1. Lower correction speed:
   ```bash
   python auto-tune.py --autotune --correction-speed 0.1
   ```
2. Increase threshold:
   ```bash
   python auto-tune.py --autotune --threshold 50
   ```
3. Reduce mix (blend with dry):
   ```python
   # In code
   AutoTuneSettings(mix=0.7)
   ```
4. Enable formant preservation (default)

#### Correction Too Slow / Notes Not Corrected
**Symptoms**: Off-pitch notes not corrected

**Solutions**:
1. Increase correction speed:
   ```bash
   python auto-tune.py --autotune --correction-speed 0.8
   ```
2. Decrease threshold:
   ```bash
   python auto-tune.py --autotune --threshold 10
   ```
3. Check key/scale matches song

#### Formant Shifting (Chipmunk Effect)
**Symptoms**: Corrected pitch sounds like chipmunk or deep voice

**Solutions**:
1. Ensure formant preservation enabled (default)
2. Limit max correction range:
   ```python
   AutoTuneSettings(max_correction_cents=200)  # ±2 semitones max
   ```
3. Use smaller pitch shifts (sing closer to target pitch)

### Harmoniser Issues

#### Harmonies Out of Tune
**Symptoms**: Generated harmonies don't match key

**Solutions**:
1. Verify key/scale matches song
2. Use `--chord-mode scale` for diatonic harmonies:
   ```bash
   python auto-tune.py --harmonise --key C --scale major --chord-mode scale
   ```
3. Check intervals are correct for mode:
   - Major: `4,7` (M3, P5)
   - Minor: `3,7` (m3, P5)

#### Harmonies Too Loud / Clipping
**Symptoms**: Distortion when harmonies added

**Solutions**:
1. Reduce voice volumes:
   ```bash
   python auto-tune.py --harmonise --voice-volumes 1.0,0.5,0.4
   ```
2. Enable soft limiting (default)
3. Reduce lead mix:
   ```bash
   python auto-tune.py --harmonise --lead-mix 0.8
   ```

#### Harmony Voices Lag Behind
**Symptoms**: Harmonies noticeably delayed

**Solutions**:
1. This is inherent to pitch shifting latency (~40ms)
2. Reduce pitch shifter FFT size (code change)
3. Accept as limitation of phase vocoder approach

### Technical Issues

#### Import Errors
**Error**: `ModuleNotFoundError: No module named 'sounddevice'`

**Solution**:
```bash
pip install sounddevice numpy scipy
```

**Error**: `OSError: PortAudio library not found`

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev

# macOS
brew install portaudio

# Windows
# Usually works with pip wheels
```

#### Permission Denied (Linux)
**Error**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
sudo usermod -a -G audio $USER
# Log out and back in
```

#### Device Busy
**Error**: `PortAudioError: Device unavailable`

**Solutions**:
1. Close other audio apps (browser, DAW, etc.)
2. Kill pulseaudio/pipewire temporarily:
   ```bash
   pulseaudio -k
   # or
   systemctl --user stop pipewire
   ```
3. Use different device index

#### Python Version Issues
**Error**: `SyntaxError` or `ModuleNotFoundError` for standard library

**Solution**: Use Python 3.10+
```bash
python --version
# Should be 3.10 or higher
```

### Performance Issues

#### High CPU Usage
**Symptoms**: System sluggish, fan noise, audio dropouts

**Solutions**:
1. Increase block size: `--block-size 512`
2. Reduce sample rate: `--sample-rate 44100`
3. Close other applications
4. Profile to find bottlenecks:
   ```bash
   python -m cProfile -o profile.stats auto-tune.py --autotune
   ```

#### Memory Leak / Growing Memory
**Symptoms**: Memory usage increases over time

**Solutions**:
1. Report as bug with reproduction steps
2. Check for arrays accumulating in lists
3. Ensure `reset()` called properly on stream restart

## Debugging Commands

### Enable Verbose Logging
```bash
# Info level
python auto-tune.py --autotune -v

# Debug level (shows pitch, processing time)
python auto-tune.py --autotune -vv

# Trace level (per-block details)
python auto-tune.py --autotune -vvv
```

### List All Devices
```bash
python auto-tune.py --list-devices
```

### Test Audio Loopback
```bash
# Record 5 seconds
python -c "
import sounddevice as sd
import numpy as np
rec = sd.rec(int(5*48000), samplerate=48000, channels=1)
sd.wait()
print(f'Recorded: {rec.shape}, min={rec.min():.3f}, max={rec.max():.3f}')
"
```

### Check Pitch Detection on File
```bash
python -c "
import numpy as np
from scipy.io import wavfile
from processing.pitch_detector import PitchDetector

sr, data = wavfile.read('test.wav')
data = data.astype(np.float32) / 32768.0
detector = PitchDetector(sr)
for i in range(0, len(data), 256):
    block = data[i:i+256]
    if len(block) == 256:
        result = detector.process(block)
        if result.voiced:
            print(f'{i/sr:.2f}s: {result.frequency:.1f}Hz conf={result.confidence:.2f}')
"
```

## Getting Help

### Before Reporting Issues
1. Run with `-vv` and capture output
2. Note: OS, Python version, audio hardware
3. Test with `--list-devices` output
4. Try minimal reproduction case

### Useful Information to Include
```bash
# System info
python -c "import platform, sys; print(f'Python {sys.version}'); print(f'Platform {platform.platform()}')"

# Audio devices
python auto-tune.py --list-devices

# Version
python auto-tune.py --version
```

### Known Limitations
1. **Latency**: Phase vocoder adds ~40ms algorithmic latency
2. **Polyphony**: Single-pitch detector, not suitable for chords input
3. **Formants**: Preservation works best for ±1 octave shifts
4. **Real-time**: Not hard real-time; occasional xruns possible under load
5. **Platform**: Best on Linux/macOS; Windows has higher baseline latency

## FAQ

**Q: Can I use this with a DAW?**
A: Not directly as a plugin yet. Use virtual audio cable (VB-Cable, BlackHole) to route audio.

**Q: Does it work with Bluetooth headphones?**
A: Yes, but Bluetooth adds ~100-300ms latency. Use wired for performance.

**Q: Can I process stereo audio?**
A: Currently mono-only processing. Stereo input uses channel 0, output duplicates to all channels.

**Q: How do I save the processed audio?**
A: Not built-in yet. Use OS recording or modify code to write WAV file.

**Q: Is there a GUI?**
A: CLI only currently. GUI planned for Phase 7.

**Q: Can I use MIDI keyboard to control harmonies?**
A: Not yet. Planned for Phase 7 (MIDI input support).