# Tests for Music Notes Module

"""Tests for note/frequency/MIDI conversions."""

import numpy as np
import pytest

from music import (
    A4_FREQ,
    A4_MIDI,
    cents_between,
    cents_to_ratio,
    freq_to_midi,
    get_note_info,
    midi_to_freq,
    midi_to_note_name,
    note_name_to_midi,
    ratio_to_cents,
    transpose_freq,
)


class TestMidiFreqConversion:
    """Test MIDI <-> Frequency conversions."""

    def test_a4_reference(self):
        """A4 (MIDI 69) should be 440 Hz."""
        assert midi_to_freq(69) == pytest.approx(440.0, rel=1e-10)
        assert freq_to_midi(440.0) == pytest.approx(69.0, rel=1e-10)

    def test_octave_relationships(self):
        """Each octave should double/halve frequency."""
        for midi in range(24, 96, 12):
            freq = midi_to_freq(midi)
            freq_octave_up = midi_to_freq(midi + 12)
            freq_octave_down = midi_to_freq(midi - 12)
            assert freq_octave_up == pytest.approx(freq * 2, rel=1e-10)
            assert freq_octave_down == pytest.approx(freq / 2, rel=1e-10)

    def test_semitone_relationships(self):
        """Each semitone should be 2^(1/12) ratio."""
        ratio = 2 ** (1 / 12)
        for midi in range(24, 96):
            freq = midi_to_freq(midi)
            freq_up = midi_to_freq(midi + 1)
            assert freq_up == pytest.approx(freq * ratio, rel=1e-10)

    def test_roundtrip(self):
        """MIDI -> freq -> MIDI should be identity."""
        for midi in np.arange(24, 96, 0.5):
            freq = midi_to_freq(midi)
            midi_back = freq_to_midi(freq)
            assert midi_back == pytest.approx(midi, abs=1e-10)

    def test_zero_frequency(self):
        """Zero frequency should return MIDI 0."""
        assert freq_to_midi(0) == 0.0
        assert freq_to_midi(-1) == 0.0


class TestNoteNames:
    """Test note name parsing and formatting."""

    def test_note_name_to_midi(self):
        """Test parsing note names."""
        assert note_name_to_midi("C4") == 60
        assert note_name_to_midi("A4") == 69
        assert note_name_to_midi("C#4") == 61
        assert note_name_to_midi("Db4") == 61
        assert note_name_to_midi("F#3") == 54
        assert note_name_to_midi("Bb5") == 82

    def test_midi_to_note_name(self):
        """Test formatting MIDI to note names."""
        assert midi_to_note_name(60) == "C4"
        assert midi_to_note_name(69) == "A4"
        assert midi_to_note_name(61) == "C#4"
        assert midi_to_note_name(61, prefer_sharps=False) == "Db4"

    def test_roundtrip_note_names(self):
        """Note name -> MIDI -> note name should be identity (with sharps)."""
        for name in ["C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4"]:
            midi = note_name_to_midi(name)
            back = midi_to_note_name(midi)
            assert back == name

    def test_invalid_note_names(self):
        """Test invalid note names raise errors."""
        with pytest.raises(ValueError):
            note_name_to_midi("H4")
        with pytest.raises(ValueError):
            note_name_to_midi("C")
        with pytest.raises(ValueError):
            note_name_to_midi("C99")


class TestCentsConversion:
    """Test cents <-> ratio conversions."""

    def test_semitone_to_cents(self):
        """1 semitone = 100 cents."""
        ratio = 2 ** (1 / 12)
        cents = ratio_to_cents(ratio)
        assert cents == pytest.approx(100.0, rel=1e-10)

    def test_octave_to_cents(self):
        """1 octave = 1200 cents."""
        cents = ratio_to_cents(2.0)
        assert cents == pytest.approx(1200.0, rel=1e-10)

    def test_cents_to_ratio(self):
        """Cents to ratio conversion."""
        ratio = cents_to_ratio(100)
        assert ratio == pytest.approx(2 ** (1 / 12), rel=1e-10)

    def test_roundtrip(self):
        """Cents -> ratio -> cents should be identity."""
        for cents in [0, 50, 100, 200, 300, 1200]:
            ratio = cents_to_ratio(cents)
            back = ratio_to_cents(ratio)
            assert back == pytest.approx(cents, rel=1e-10)

    def test_cents_between(self):
        """Test cents between two frequencies."""
        # 440 to 880 = +1200 cents (octave)
        assert cents_between(440, 880) == pytest.approx(1200.0, rel=1e-10)
        # 440 to 220 = -1200 cents
        assert cents_between(440, 220) == pytest.approx(-1200.0, rel=1e-10)
        # 440 to 466.16 (A#) ≈ +100 cents
        assert cents_between(440, 466.16) == pytest.approx(100.0, abs=1.0)


class TestTranspose:
    """Test frequency transposition."""

    def test_transpose_up(self):
        """Transpose up by semitones."""
        result = transpose_freq(440, 12)
        assert result == pytest.approx(880, rel=1e-10)

    def test_transpose_down(self):
        """Transpose down by semitones."""
        result = transpose_freq(440, -12)
        assert result == pytest.approx(220, rel=1e-10)

    def test_transpose_fractional(self):
        """Transpose by fractional semitones (cents)."""
        result = transpose_freq(440, 0.5)  # 50 cents
        expected = 440 * 2 ** (0.5 / 12)
        assert result == pytest.approx(expected, rel=1e-10)


class TestNoteInfo:
    """Test get_note_info utility."""

    def test_in_tune_note(self):
        """Test perfectly in-tune note."""
        info = get_note_info(440.0)
        assert info["note_name"] == "A4"
        assert info["midi_rounded"] == 69
        assert info["cents_off"] == pytest.approx(0.0, abs=0.1)
        assert info["is_in_tune"]

    def test_sharp_note(self):
        """Test sharp note."""
        info = get_note_info(466.1637615180899)  # A#4 exact
        assert info["note_name"] == "A#4"
        assert abs(info["cents_off"]) < 1  # Should be very close to 0

    def test_flat_note(self):
        """Test flat note."""
        info = get_note_info(415.3046975799451)  # Ab4 exact
        # Note name uses sharps by default, so G#4 is correct
        assert info["note_name"] in ("G#4", "Ab4")
        assert abs(info["cents_off"]) < 1


class TestConstants:
    """Test module constants."""

    def test_a4_constants(self):
        """Test A4 reference constants."""
        assert A4_FREQ == 440.0
        assert A4_MIDI == 69


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
