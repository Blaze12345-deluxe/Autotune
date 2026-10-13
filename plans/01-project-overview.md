# Project Overview: Real-Time Python Auto-Tune & Harmoniser

## Vision
Create a professional-grade, real-time vocal processing application written in Python that captures audio from a microphone, processes it with either Auto-Tune (pitch correction) or a Harmoniser (harmony generation), and outputs the processed audio through speakers or headphones with minimal latency.

## Core Objectives
1. **Real-time performance** - Process audio blocks continuously with < 20ms latency
2. **Modular architecture** - Separate audio I/O, pitch detection, pitch shifting, and musical logic
3. **Extensibility** - Easy to add new effects, processors, and algorithms
4. **Musical intelligence** - Proper scale/chord awareness for natural-sounding correction/harmonies
5. **Professional quality** - Phase-vocoder based pitch shifting, not simple resampling

## Target Use Cases
- Live vocal performance with real-time pitch correction
- Practice tool for singers learning pitch accuracy
- Real-time harmony generation for solo performers
- Educational tool for understanding vocal processing
- Foundation for future GUI/DAW plugin development

## Success Metrics
- Starts and runs without crashes for 30+ minutes
- Latency < 20ms end-to-end (at 48kHz, 256-sample blocks)
- Clean pitch correction without artifacts on sustained vowels
- Harmonies stay in tune with selected key/scale
- Graceful handling of silence, unvoiced sounds, and unreliable pitch
- Clean shutdown on Ctrl+C