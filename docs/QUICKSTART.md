# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

**Using uv (recommended):**
```bash
# Install uv if needed
pip install uv

# Linux (Ubuntu/Debian)
sudo apt-get install portaudio19-dev python3-dev

# macOS
brew install portaudio

# Windows - no system deps needed

# Create venv and install
uv sync
```

**Using pip (traditional):**
```bash
# Linux (Ubuntu/Debian)
sudo apt-get install portaudio19-dev python3-dev
pip install sounddevice numpy scipy

# macOS
brew install portaudio
pip install sounddevice numpy scipy

# Windows
pip install sounddevice numpy scipy
```

### 2. Verify Installation
```bash
# With uv
uv run python -c "import sounddevice as sd; print(sd.query_devices())"

# With pip
python -c "import sounddevice as sd; print(sd.query_devices())"
```
Should list your audio devices without errors.

### 3. Run Auto-Tune
```bash
# With uv
uv run python auto-tune.py --autotune --key C --scale major

# With pip
python auto-tune.py --autotune --key C --scale major

# Sing into your microphone - you'll hear corrected pitch in headphones
```

### 4. Run Harmoniser
```bash
# Generate harmonies (major third + fifth)
python auto-tune.py --harmonise --key C --scale major --intervals 4,7
```

## Common Configurations

### For Vocal Practice (Natural Correction)
```bash
python auto-tune.py --autotune \
  --key G --scale major \
  --correction-speed 0.2 \
  --threshold 50 \
  -v
```
- Slow correction preserves natural expression
- Only corrects obvious pitch errors (>50 cents)
- Verbose output shows detected pitch

### For "T-Pain" Effect (Hard Tuning)
```bash
python auto-tune.py --autotune \
  --key C --scale major \
  --correction-speed 1.0 \
  --threshold 0 \
  --block-size 128
```
- Instant correction
- Corrects every note
- Smaller block for lower latency

### For Live Harmony (Backup Vocals)
```bash
python auto-tune.py --harmonise \
  --key A --scale minor \
  --intervals 3,7 \
  --voice-volumes 1.0,0.6 \
  --block-size 256
```
- Minor third + perfect fifth above melody
- Harmony at 60% volume
- Standard block size for stability

### For Choir Effect (Multiple Voices)
```bash
python auto-tune.py --harmonise \
  --key F --scale major \
  --intervals -12,4,7,12 \
  --voice-volumes 0.8,0.5,0.5,0.4 \
  --chord-mode scale
```
- 4 voices: octave down, third, fifth, octave up
- Diatonic harmonies (follow scale)
- Decreasing volumes for natural blend

## Device Selection

### List Devices
```bash
python auto-tune.py --list-devices
```

### Use Specific Devices
```bash
# By index (from --list-devices)
python auto-tune.py --autotune --input-device 2 --output-device 3

# By name (substring match)
python auto-tune.py --autotune --input-device "Focusrite" --output-device "Headphones"
```

## Latency Optimization

### Low Latency (Performance)
```bash
python auto-tune.py --autotune --block-size 128 --sample-rate 48000
```
- ~2.7ms block time
- Higher CPU usage
- Good for live performance

### Stable (Recording/Practice)
```bash
python auto-tune.py --autotune --block-size 512 --sample-rate 44100
```
- ~11.6ms block time
- Lower CPU usage
- Fewer dropouts

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| No sound | `--output-device 0` |
| No mic input | `--input-device 0` |
| Clicks/pops | `--block-size 512` |
| High latency | `--block-size 128` |
| Wrong key | `--key <your_key> --scale <your_scale>` |
| Too robotic | `--correction-speed 0.2 --threshold 50` |
| Harmonies clash | `--chord-mode scale` |

## Keyboard Shortcuts (While Running)
- `Ctrl+C` - Clean shutdown
- No other hotkeys currently (planned for GUI version)

## Next Steps

1. **Read full CLI reference**: `docs/CLI_REFERENCE.md`
2. **Understand architecture**: `docs/ARCHITECTURE.md`
3. **Customize settings**: Edit `config/defaults.py`
4. **Run tests**: `pip install -r requirements-dev.txt && pytest`
5. **Contribute**: See `docs/DEVELOPER_GUIDE.md`

## Verify Installation

```bash
# Run unit tests (63 tests passing)
pytest -v
```

## Example Session

```bash
# 1. Check your devices
$ python auto-tune.py --list-devices
Input Devices:
  0: Built-in Microphone
  1: USB Audio Device *
Output Devices:
  0: Built-in Output
  1: USB Audio Device *
  2: Bluetooth Headphones

# 2. Run with your USB interface
$ python auto-tune.py --autotune --key C --scale major --input-device 1 --output-device 1 -v
[INFO] Starting Auto-Tune in C major
[INFO] Input: USB Audio Device (2 ch @ 48000Hz)
[INFO] Output: USB Audio Device (2 ch @ 48000Hz)
[INFO] Block size: 256 samples (5.3ms)
[INFO] Press Ctrl+C to stop
[INFO] Pitch: 261.6Hz (C4) conf=0.92
[INFO] Pitch: 293.7Hz (D4) conf=0.89
[INFO] Pitch: 329.6Hz (E4) conf=0.94
...

# 3. Sing! Press Ctrl+C when done
^C
[INFO] Stopping...
[INFO] Blocks processed: 12450
[INFO] Overruns: 0, Underruns: 0
[INFO] Avg processing: 1.2ms
[INFO] Goodbye!
```