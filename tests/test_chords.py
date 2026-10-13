# Tests for Music Chords Module

"""Tests for chord definitions, construction, and voicing."""

import numpy as np
import pytest

from music import (
    Chord, get_diatonic_chords, chord_from_degree, get_chord_notes,
    voice_lead_chords, get_chord_symbol, parse_chord_symbol,
    CHORD_QUALITIES
)


class TestChordQualities:
    """Test chord quality definitions."""
    
    def test_triad_qualities(self):
        """Test basic triad qualities."""
        assert CHORD_QUALITIES['major'] == [0, 4, 7]
        assert CHORD_QUALITIES['minor'] == [0, 3, 7]
        assert CHORD_QUALITIES['diminished'] == [0, 3, 6]
        assert CHORD_QUALITIES['augmented'] == [0, 4, 8]
    
    def test_seventh_qualities(self):
        """Test seventh chord qualities."""
        assert CHORD_QUALITIES['dom7'] == [0, 4, 7, 10]
        assert CHORD_QUALITIES['maj7'] == [0, 4, 7, 11]
        assert CHORD_QUALITIES['min7'] == [0, 3, 7, 10]
        assert CHORD_QUALITIES['half_dim7'] == [0, 3, 6, 10]
        assert CHORD_QUALITIES['dim7'] == [0, 3, 6, 9]


class TestChordClass:
    """Test Chord class."""
    
    def test_chord_creation(self):
        """Test creating chord from root MIDI."""
        chord = Chord(60, 'major')  # C4 major
        assert chord.root_midi == 60
        assert chord.quality == 'major'
        assert chord.notes == [60, 64, 67]  # C, E, G
    
    def test_chord_from_name(self):
        """Test creating chord from note name."""
        chord = Chord.from_root_name('C4', 'major')
        assert chord.root_midi == 60
        assert chord.notes == [60, 64, 67]
    
    def test_chord_frequencies(self):
        """Test getting chord frequencies."""
        chord = Chord(60, 'major')
        freqs = chord.get_frequencies()
        assert len(freqs) == 3
        assert freqs[0] == pytest.approx(261.63, rel=0.01)  # C4
        assert freqs[1] == pytest.approx(329.63, rel=0.01)  # E4
        assert freqs[2] == pytest.approx(392.00, rel=0.01)  # G4
    
    def test_chord_transpose(self):
        """Test chord transposition."""
        chord = Chord(60, 'major')  # C major
        transposed = chord.transpose(2)  # Up whole step
        assert transposed.root_midi == 62  # D
        assert transposed.notes == [62, 66, 69]  # D, F#, A
    
    def test_chord_inversions(self):
        """Test chord inversions."""
        chord = Chord(60, 'major')  # C, E, G
        root_pos = chord.invert(0)  # C, E, G
        first_inv = chord.invert(1)  # E, G, C
        second_inv = chord.invert(2)  # G, C, E
        
        assert root_pos == [60, 64, 67]
        assert first_inv == [64, 67, 72]  # E4, G4, C5
        assert second_inv == [67, 72, 76]  # G4, C5, E5
    
    def test_chord_voicing(self):
        """Test chord voicing in specific octave."""
        chord = Chord(60, 'major')
        voicing = chord.get_voicing(inversion=0, octave=4)
        # Should be around C4, E4, G4
        assert all(60 <= n < 72 for n in voicing)
    
    def test_chord_symbol(self):
        """Test chord symbol generation."""
        chord = Chord(60, 'major')
        assert get_chord_symbol(chord) == 'C'
        
        chord = Chord(69, 'minor')  # A minor
        assert get_chord_symbol(chord) == 'Am'
        
        chord = Chord(67, 'dom7')  # G7
        assert get_chord_symbol(chord) == 'G7'
        
        chord = Chord(65, 'maj7')  # Fmaj7
        assert get_chord_symbol(chord) == 'Fmaj7'
    
    def test_chord_repr(self):
        """Test chord string representation."""
        chord = Chord(60, 'major')
        assert 'C4' in repr(chord)
        assert 'major' in repr(chord)


class TestDiatonicChords:
    """Test diatonic chord generation."""
    
    def test_c_major_diatonic(self):
        """Test diatonic chords in C major."""
        chords = get_diatonic_chords('C', 'major')
        
        # I = C major
        assert chords[1].quality == 'major'
        assert chords[1].notes == [60, 64, 67]
        
        # ii = D minor
        assert chords[2].quality == 'minor'
        assert chords[2].notes[0] == 62  # D
        
        # iii = E minor
        assert chords[3].quality == 'minor'
        
        # IV = F major
        assert chords[4].quality == 'major'
        
        # V = G major
        assert chords[5].quality == 'major'
        
        # vi = A minor
        assert chords[6].quality == 'minor'
        
        # vii° = B diminished
        assert chords[7].quality == 'diminished'
    
    def test_a_minor_diatonic(self):
        """Test diatonic chords in A minor."""
        chords = get_diatonic_chords('A', 'minor')
        
        # i = A minor
        assert chords[1].quality == 'minor'
        
        # ii° = B diminished
        assert chords[2].quality == 'diminished'
        
        # III = C major
        assert chords[3].quality == 'major'
        
        # iv = D minor
        assert chords[4].quality == 'minor'
        
        # v = E minor
        assert chords[5].quality == 'minor'
        
        # VI = F major
        assert chords[6].quality == 'major'
        
        # VII = G major
        assert chords[7].quality == 'major'
    
    def test_harmonic_minor_diatonic(self):
        """Test diatonic chords in harmonic minor."""
        chords = get_diatonic_chords('A', 'harmonic_minor')
        
        # i = A minor
        assert chords[1].quality == 'minor'
        
        # III+ = C augmented
        assert chords[3].quality == 'augmented'
        
        # V = E major (raised 7th)
        assert chords[5].quality == 'major'


class TestChordFromDegree:
    """Test chord_from_degree function."""
    
    def test_get_specific_degree(self):
        """Test getting chord for specific degree."""
        chord = chord_from_degree('C', 'major', 1)  # I
        assert chord.quality == 'major'
        
        chord = chord_from_degree('C', 'major', 5)  # V
        assert chord.quality == 'major'
        
        # Override quality
        chord = chord_from_degree('C', 'major', 1, 'minor')
        assert chord.quality == 'minor'


class TestVoiceLeading:
    """Test voice leading between chords."""
    
    def test_voice_leading_c_to_f(self):
        """Test voice leading from C major to F major."""
        c_major = Chord(60, 'major')
        f_major = Chord(65, 'major')
        
        voiced = voice_lead_chords(c_major, f_major)
        # Should find smooth voice leading
        assert len(voiced) == 3
    
    def test_voice_leading_minimal_movement(self):
        """Test voice leading minimizes movement."""
        c_major = Chord(60, 'major')  # C, E, G
        # C major in different voicing
        g_major = Chord(67, 'major')  # G, B, D
        
        voiced = voice_lead_chords(c_major, g_major)
        # Movement should be relatively small
        movements = [abs(v - c) for v, c in zip(voiced, c_major.notes)]
        total_movement = sum(movements)
        assert total_movement <= 21  # Should be reasonably smooth


class TestChordSymbolParsing:
    """Test parsing chord symbols."""
    
    def test_parse_basic_symbols(self):
        """Test parsing basic chord symbols."""
        root, quality = parse_chord_symbol('C')
        assert root == 'C'
        assert quality == 'major'
        
        root, quality = parse_chord_symbol('Am')
        assert root == 'A'
        assert quality == 'minor'
        
        root, quality = parse_chord_symbol('C#m')
        assert root == 'C#'
        assert quality == 'minor'
        
        root, quality = parse_chord_symbol('Bb')
        assert root == 'Bb'
        assert quality == 'major'
    
    def test_parse_seventh_chords(self):
        """Test parsing seventh chord symbols."""
        root, quality = parse_chord_symbol('G7')
        assert root == 'G'
        assert quality == 'dom7'
        
        root, quality = parse_chord_symbol('Cmaj7')
        assert root == 'C'
        assert quality == 'maj7'
        
        root, quality = parse_chord_symbol('Dm7')
        assert root == 'D'
        assert quality == 'min7'
    
    def test_parse_diminished_augmented(self):
        """Test parsing dim/aug symbols."""
        root, quality = parse_chord_symbol('Cdim')
        assert quality == 'diminished'
        
        root, quality = parse_chord_symbol('Caug')
        assert quality == 'augmented'
        
        root, quality = parse_chord_symbol('C+')
        assert quality == 'augmented'


class TestGetChordNotes:
    """Test get_chord_notes function."""
    
    def test_get_chord_frequencies(self):
        """Test getting frequencies of diatonic chord."""
        freqs = get_chord_notes('C', 'major', 1)  # I chord in C major
        assert len(freqs) == 3
        # C major: C4, E4, G4
        assert freqs[0] == pytest.approx(261.63, rel=0.01)
        assert freqs[1] == pytest.approx(329.63, rel=0.01)
        assert freqs[2] == pytest.approx(392.00, rel=0.01)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])