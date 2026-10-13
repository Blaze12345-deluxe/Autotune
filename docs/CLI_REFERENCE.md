# CLI Reference

## Synopsis
```bash
python auto-tune.py [OPTIONS]
```

## Description
Real-time vocal Auto-Tune and Harmoniser. Captures microphone audio, processes it in real-time, and plays the result through speakers or headphones.

**One mode is required**: `--autotune` or `--harmonise` (mutually exclusive).

## Options

### Mode Selection (Required, Mutually Exclusive)

#### `--autotune`
Enable pitch correction (Auto-Tune) mode.
- Corrects incoming pitch to nearest note in selected key/scale
- Adjustable correction speed and threshold

#### `--harmonise`
Enable harmony generation mode.
- Generates additional voices at specified intervals
- Multiple harmony modes available

### Musical Options

#### `--key KEY`
Musical key for pitch quantization.
- **Default**: `C`
- **Choices**: `C`, `C#`, `Db`, `D`, `D#`, `Eb`, `E`, `F`, `F#`, `Gb`, `G`, `G#`, `Ab`, `A`, `A#`, `Bb`, `B`
- Case-insensitive, accepts both sharps (`#`) and flats (`b`)

#### `--scale SCALE`
Musical scale for pitch quantization.
- **Default**: `major`
- **Choices**:
  - `major` - Major (Ionian)
  - `minor` - Natural minor (Aeolian)
  - `harmonic_minor` - Harmonic minor
  - `melodic_minor` - Melodic minor
  - `pentatonic_major` - Major pentatonic
  - `pentatonic_minor` - Minor pentatonic
  - `blues` - Blues scale
  - `dorian` - Dorian mode
  - `phrygian` - Phrygian mode
  - `lydian` - Lydian mode
  - `mixolydian` - Mixolydian mode
  - `locrian` - Locrian mode
  - `chromatic` - All 12 semitones
  - `whole_tone` - Whole tone scale
  - `diminished` - Half-whole diminished

### Audio Device Options

#### `--input-device DEVICE`
Select input (microphone) device.
- **Default**: System default input device
- **Format**: Device index (integer) or name substring (string)
- Use `--list-devices` to see available devices

#### `--output-device DEVICE`
Select output (speaker/headphone) device.
- **Default**: System default output device
- **Format**: Device index (integer) or name substring (string)
- Use `--list-devices` to see available devices

#### `--sample-rate RATE`
Audio sample rate in Hz.
- **Default**: `48000`
- **Typical values**: `44100`, `48000`, `88200`, `96000`
- Must be supported by selected devices

#### `--block-size SIZE`
Audio block size in samples.
- **Default**: `256`
- **Range**: `64` to `1024` (power of 2 recommended)
- Lower = less latency, higher CPU load
- Higher = more stable, more latency

#### `--channels CHANNELS`
Number of input channels.
- **Default**: `1` (mono)
- **Note**: Only first channel is processed; others passed through

### Auto-Tune Options (Only with `--autotune`)

#### `--correction-speed SPEED`
Pitch correction speed.
- **Default**: `0.5`
- **Range**: `0.0` to `1.0`
- `0.0` = Slow/natural correction (preserves vibrato, slides)
- `1.0` = Instant/robotic correction (T-Pain effect)
- Intermediate values blend between both

#### `--threshold CENTS`
Correction threshold in cents (100 cents = 1 semitone).
- **Default**: `25`
- **Range**: `0` to `1200`
- Only correct notes that are off by more than this amount
- `0` = Correct everything (hard tuning)
- Higher values = more natural, only fix obvious errors

### Harmoniser Options (Only with `--harmonise`)

#### `--intervals INTERVALS`
Semitone intervals for harmony voices (comma-separated).
- **Default**: `3,7` (minor third + perfect fifth = minor triad)
- **Format**: Comma-separated integers (positive or negative)
- **Examples**:
  - `4,7` - Major third + perfect fifth (major triad)
  - `3,7` - Minor third + perfect fifth (minor triad)
  - `7,12` - Perfect fifth + octave (power chord)
  - `-12,3,7` - Octave down + third + fifth
  - `4,7,11` - Major triad + major seventh

#### `--voice-volumes VOLUMES`
Volume level for each voice (comma-separated).
- **Default**: `1.0,0.7,0.7`
- **Format**: Comma-separated floats (0.0 to 1.0+)
- First value = lead/original voice
- Subsequent values = harmony voices
- **Examples**:
  - `1.0,0.5` - Lead at full, one harmony at half
  - `0.8,0.6,0.6` - Balanced three-part harmony
  - `1.0,0.8,0.6,0.4` - Four voices, decreasing volume

#### `--chord-mode MODE`
Harmony generation mode.
- **Default**: `intervals`
- **Choices**:
  - `intervals` - Fixed semitone intervals above detected pitch
  - `scale` - Diatonic harmonies following key/scale
  - `chord` - Harmonize to current chord (uses `--chord-quality`)

#### `--chord-quality QUALITY`
Chord quality for `chord` mode.
- **Default**: `major`
- **Choices**: `major`, `minor`, `diminished`, `augmented`, `dom7`, `maj7`, `min7`, `half_dim7`, `dim7`

### Utility Options

#### `--list-devices`
List all available audio input and output devices and exit.
Shows: device index, name, max input/output channels, default sample rate.

#### `--list-scales`
List all available musical scales and exit.

#### `-v, --verbose`
Increase verbosity. Can be repeated:
- `-v` : Info level (device info, settings)
- `-vv` : Debug level (processing stats, pitch detection)
- `-vvv` : Trace level (per-block timing, buffer status)

#### `--version`
Show program version and exit.

#### `-h, --help`
Show help message and exit.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (clean shutdown) |
| `1` | General error |
| `2` | Invalid command-line arguments |
| `3` | Audio device error (not found, busy, etc.) |
| `4` | Processing initialization error |
| `130` | Interrupted by signal (Ctrl+C) |

## Examples

### Auto-Tune
```bash
# Basic usage
python auto-tune.py --autotune --key C --scale major

# Natural correction for practice
python auto-tune.py --autotune --key G --scale major --correction-speed 0.2 --threshold 50

# Hard correction effect
python auto-tune.py --autotune --key A --scale minor --correction-speed 1.0 --threshold 0

# Custom audio devices
python auto-tune.py --autotune --input-device "Focusrite" --output-device "Headphones"

# Low latency
python auto-tune.py --autotune --block-size 128 --sample-rate 48000
```

### Harmoniser
```bash
# Basic major harmony
python auto-tune.py --harmonise --key C --scale major --intervals 4,7

# Minor harmony
python auto-tune.py --harmonise --key A --scale minor --intervals 3,7

# Diatonic (scale-aware) harmony
python auto-tune.py --harmonise --key G --scale major --chord-mode scale

# Three-part harmony
python auto-tune.py --harmonise --key C --scale major --intervals 4,7,12 --voice-volumes 1.0,0.6,0.5

# Choir-like (octave down + third + fifth + octave up)
python auto-tune.py --harmonise --key F --scale major --intervals -12,4,7,12 --voice-volumes 0.8,0.5,0.5,0.4

# Power chord style
python auto-tune.py --harmonise --key E --scale major --intervals 7,12 --voice-volumes 1.0,0.8,0.6
```

### Utility
```bash
# List devices
python auto-tune.py --list-devices

# List scales
python auto-tune.py --list-scales

# Verbose output
python auto-tune.py --autotune -v

# Debug output
python auto-tune.py --harmonise -vv
```

## Device Selection Tips

### Finding Device Names
```bash
python auto-tune.py --list-devices
```

Output example:
```
Input Devices:
  0: Built-in Microphone (2 in, 0 out) @ 48000Hz
  1: USB Audio Device (2 in, 2 out) @ 48000Hz
  2: Focusrite Scarlett 2i2 (2 in, 2 out) @ 96000Hz *

Output Devices:
  0: Built-in Output (0 in, 2 out) @ 48000Hz
  1: USB Audio Device (2 in, 2 out) @ 48000Hz
  2: Focusrite Scarlett 2i2 (2 in, 2 out) @ 96000Hz *
  3: Bluetooth Headphones (0 in, 2 out) @ 48000Hz
```

### Selecting Devices
```bash
# By index
python auto-tune.py --autotune --input-device 2 --output-device 2

# By name substring (case-insensitive)
python auto-tune.py --autotune --input-device "Focusrite" --output-device "Headphones"
```

## Troubleshooting

### "No input device found"
```bash
# List devices first
python auto-tune.py --list-devices

# Try default explicitly
python auto-tune.py --autotune --input-device 0
```

### "Device busy" / "Access denied"
- Close other audio applications
- On Linux: ensure user in `audio` group
- On Windows: check exclusive mode settings

### High latency / glitches
```bash
# Try larger block size
python auto-tune.py --autotune --block-size 512

# Or lower sample rate
python auto-tune.py --autotune --sample-rate 44100
```

### Can't hear output
- Check `--output-device` matches your headphones
- Check system volume mixer
- Try `--output-device 0` (usually default)