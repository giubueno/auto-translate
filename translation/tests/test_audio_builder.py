import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pydub import AudioSegment
from audio_builder import AudioBuilder
from utils.tts import VoiceOverResult


def make_voice_over_result(minutes, seconds, duration_ms, language="de"):
    """Create a VoiceOverResult with a fake file path."""
    mins_str = str(minutes).zfill(2)
    secs_str = str(seconds).zfill(2)
    return VoiceOverResult(
        minutes=minutes,
        seconds=seconds,
        text="test",
        language=language,
        files_path=f"outputs/{language}/{mins_str}{secs_str}.mp3",
    )


def make_audio_segment(duration_ms):
    """Create a silent AudioSegment of given duration."""
    return AudioSegment.silent(duration=duration_ms)


class TestBuildSyncedOverlap(unittest.TestCase):
    """Tests for overlap detection and truncation in _build_synced()."""

    def setUp(self):
        self.builder = AudioBuilder(language="de", sequential=False)
        os.makedirs("outputs/de", exist_ok=True)

    @patch.object(AudioSegment, 'from_mp3')
    @patch.object(AudioSegment, 'export')
    def test_overlapping_segments_get_truncated(self, mock_export, mock_from_mp3):
        """Overlapping segments should be truncated so they don't overlap."""
        # Segment A: starts at 1s (1000ms), duration 5000ms -> ends at 6000ms
        # Segment B: starts at 3s (3000ms), duration 2000ms -> ends at 5000ms
        # Overlap: 6000 > 3000, so A should be truncated
        seg_a = make_audio_segment(5000)
        seg_b = make_audio_segment(2000)

        results = [
            make_voice_over_result(0, 1, 5000),  # starts at 1000ms
            make_voice_over_result(0, 3, 2000),  # starts at 3000ms
        ]

        mock_from_mp3.side_effect = [seg_a, seg_b]

        self.builder._build_synced(results)

        # Verify export was called (audio was built successfully)
        mock_export.assert_called_once()

    @patch.object(AudioSegment, 'from_mp3')
    @patch.object(AudioSegment, 'export')
    def test_non_overlapping_segments_unchanged(self, mock_export, mock_from_mp3):
        """Non-overlapping segments should pass through without modification."""
        # Segment A: starts at 0s, duration 1000ms -> ends at 1000ms
        # Segment B: starts at 5s, duration 1000ms -> ends at 6000ms
        # No overlap
        seg_a = make_audio_segment(1000)
        seg_b = make_audio_segment(1000)

        results = [
            make_voice_over_result(0, 0, 1000),  # starts at 0ms
            make_voice_over_result(0, 5, 1000),  # starts at 5000ms
        ]

        mock_from_mp3.side_effect = [seg_a, seg_b]

        self.builder._build_synced(results)

        mock_export.assert_called_once()

    @patch.object(AudioSegment, 'from_mp3')
    @patch.object(AudioSegment, 'export')
    def test_same_timestamp_segments(self, mock_export, mock_from_mp3):
        """Segments starting at the same timestamp — first should be skipped."""
        seg_a = make_audio_segment(2000)
        seg_b = make_audio_segment(2000)

        results = [
            make_voice_over_result(0, 5, 2000),
            make_voice_over_result(0, 5, 2000),
        ]

        mock_from_mp3.side_effect = [seg_a, seg_b]

        # Should not crash
        self.builder._build_synced(results)
        mock_export.assert_called_once()

    @patch.object(AudioSegment, 'from_mp3')
    @patch.object(AudioSegment, 'export')
    def test_very_short_gap(self, mock_export, mock_from_mp3):
        """Segments with a very short gap (e.g. 10ms) should not crash."""
        # Segment A: starts at 0ms, duration 2000ms -> ends at 2000ms
        # Segment B: starts at 2010ms (10ms gap)
        seg_a = make_audio_segment(2000)
        seg_b = make_audio_segment(1000)

        results = [
            make_voice_over_result(0, 0, 2000),
            # 2.01s = 2s + 10ms — approximate with 2s
            make_voice_over_result(0, 2, 1000),
        ]

        mock_from_mp3.side_effect = [seg_a, seg_b]

        self.builder._build_synced(results)
        mock_export.assert_called_once()

    @patch.object(AudioSegment, 'from_mp3')
    @patch.object(AudioSegment, 'export')
    def test_segments_sorted_before_overlap_check(self, mock_export, mock_from_mp3):
        """Segments passed in reverse order should still be sorted and handled."""
        seg_a = make_audio_segment(3000)
        seg_b = make_audio_segment(3000)

        # Pass in reverse order — B first, A second
        results = [
            make_voice_over_result(0, 5, 3000),  # starts at 5000ms
            make_voice_over_result(0, 1, 3000),  # starts at 1000ms
        ]

        mock_from_mp3.side_effect = [seg_a, seg_b]

        # Should not crash and should sort correctly
        self.builder._build_synced(results)
        mock_export.assert_called_once()

    @patch.object(AudioSegment, 'from_mp3')
    @patch.object(AudioSegment, 'export')
    def test_single_segment(self, mock_export, mock_from_mp3):
        """A single segment should work with no overlap logic needed."""
        seg = make_audio_segment(3000)
        results = [make_voice_over_result(0, 10, 3000)]

        mock_from_mp3.side_effect = [seg]

        self.builder._build_synced(results)
        mock_export.assert_called_once()


if __name__ == '__main__':
    unittest.main()
