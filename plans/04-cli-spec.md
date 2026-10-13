# CLI Specification

## Command Structure
```bash
python auto-tune.py [OPTIONS]

Modes (mutually exclusive, one required):
  --autotune              Enable real-time pitch correction (Auto-Tune mode)
  --harmonise             Enable real-time harmony generation (Harmoniser mode)

Musical Settings:
  --key KEY               Musical key (default: C)
                          Choices: C, C#, Db, D, D#, Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, B
  --scale SCALE           Musical scale (default: major)
                          Choices: major, minor, harmonic_minor, melodic_minor, pentatonic_major,
                                   pentatonic_minor, blues, dorian, phrygian, lydian, mixolydian,
                                   locrian, chromatic

Audio Device Settings:
  --input-device ID       Input device ID or name substring (default: system default)
  --output-device ID      Output device ID or name substring (default: system default)
  --sample-rate RATE      Sample rate in Hz (default: 48000)
  --block-size SIZE       Block size in samples (default: 256)
  --channels CHANS        Number of channels (default: 1 for mono input)

Processing Settings:
  --correction-speed SPEED  Auto-Tune: correction speed 0.0-1.0 (default: 0.5)
  --threshold CENTS       Auto-Tune: only correct if off by >N cents (default: 25)
  --intervals INTERVALS   Harmoniser: comma-separated semitone intervals (default: 3,7)
  --voice-volumes VOLS    Harmoniser: comma-separated volumes for each voice (default: 1.0,0.7,0.7)
  --chord-mode MODE       Harmoniser: chord|scale|intervals (default: intervals)

Utility:
  --list-devices          List available audio devices and exit
  --list-scales           List available scales and exit
  --verbose, -v           Verbose logging (can repeat: -vv, -vvv)
  --help, -h              Show help message and exit
```

## Mutually Exclusive Group
```python
mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument('--autotune', action='store_true')
mode_group.add_argument('--harmonise', action='store_true')
```

## Key/Scale Validation
- Key: Case-insensitive, accepts sharps (#) and flats (b)
- Scale: Case-insensitive, validates against known scales
- Invalid combinations show error with valid options

## Device Selection
- Accept numeric ID or substring match on device name
- `--list-devices` shows: ID, name, max input/output channels, default sample rates
- Default: PortAudio default input/output devices

## Examples
```bash
# Basic Auto-Tune in C major
python auto-tune.py --autotune --key C --scale major

# Auto-Tune with fast correction (T-Pain style)
python auto-tune.py --autotune --key C --scale major --correction-speed 0.9 --threshold 10

# Harmoniser with major third and fifth
python auto-tune.py --harmonise --key G --scale major --intervals 4,7

# Harmoniser with custom volumes
python auto-tune.py --harmonise --key A --scale minor --intervals 3,7,12 --voice-volumes 1.0,0.6,0.5

# List audio devices
python auto-tune.py --list-devices

# Custom audio settings
python auto-tune.py --autotune --sample-rate 44100 --block-size 128 --input-device "USB" --output-device "Headphones"
```

## Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success (clean shutdown) |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Audio device error |
| 4 | Processing initialization error |
| 130 | Interrupted (SIGINT/Ctrl+C) |

## Help Output Format
```
usage: auto-tune.py [-h] (--autotune | --harmonise) [--key KEY] [--scale SCALE]
                    [--input-device INPUT_DEVICE] [--output-device OUTPUT_DEVICE]
                    [--sample-rate SAMPLE_RATE] [--block-size BLOCK_SIZE]
                    [--channels CHANNELS] [--correction-speed CORRECTION_SPEED]
                    [--threshold THRESHOLD] [--intervals INTERVALS]
                    [--voice-volumes VOICE_VOLUMES] [--chord-mode CHORD_MODE]
                    [--list-devices] [--list-scales] [-v] [--version]

Real-time vocal Auto-Tune and Harmoniser

Modes:
  --autotune         Real-time pitch correction
  --harmonise        Real-time harmony generation

Musical Options:
  --key KEY          Musical key (default: C)
  --scale SCALE      Musical scale (default: major)

Audio Options:
  --input-device ID  Input device ID or name (default: default)
  --output-device ID Output device ID or name (default: default)
  --sample-rate RATE Sample rate in Hz (default: 48000)
  --block-size SIZE  Block size in samples (default: 256)
  --channels CHANS   Input channels (default: 1)

Auto-Tune Options:
  --correction-speed SPEED  Correction speed 0.0-1.0 (default: 0.5)
  --threshold CENTS         Correction threshold in cents (default: 25)

Harmoniser Options:
  --intervals INTERVALS     Semitone intervals e.g. 3,7 (default: 3,7)
  --voice-volumes VOLS      Voice volumes e.g. 1.0,0.7,0.7 (default: 1.0,0.7,0.7)
  --chord-mode MODE         Harmony mode: chord|scale|intervals (default: intervals)

Utility:
  --list-devices      List audio devices
  --list-scales       List available scales
  -v, --verbose       Verbose output
  --version           Show version
```

## Version Flag
```bash
python auto-tune.py --version
# Output: auto-tune 0.1.0
```