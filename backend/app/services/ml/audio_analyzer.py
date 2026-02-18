"""
Audio Analyzer - analyzes speech for filler words, pauses, speech rate.
Works on text transcriptions (from WebSocket or speech-to-text).
"""
import re
from typing import Dict, List, Tuple


class AudioAnalyzer:

    # Common filler words across languages (English focus)
    FILLER_WORDS = {
        "um", "uh", "like", "you know", "basically", "literally",
        "actually", "so", "right", "okay", "hmm", "er", "ah",
        "kinda", "sorta", "i mean", "well", "yeah"
    }

    def analyze_text(self, text: str, duration_seconds: float = None) -> Dict:
        """
        Analyze transcribed text for speech patterns.

        Args:
            text: The transcribed speech text
            duration_seconds: Optional duration of speech (for speech rate)

        Returns:
            {
                "filler_words_count": int,
                "filler_words_list": [str, ...],
                "total_words": int,
                "unique_words": int,
                "speech_rate_wpm": float (if duration provided),
                "sentences": int,
                "avg_sentence_length": float
            }
        """
        if not text or not text.strip():
            return self._empty_result()

        text_lower = text.lower()
        words = self._tokenize(text)

        # Count filler words
        filler_count = 0
        found_fillers = []
        for filler in self.FILLER_WORDS:
            count = text_lower.count(f" {filler} ") + \
                    text_lower.count(f" {filler},") + \
                    text_lower.count(f" {filler}.")
            if text_lower.startswith(filler + " "):
                count += 1
            if text_lower.endswith(" " + filler):
                count += 1
            if count > 0:
                filler_count += count
                found_fillers.extend([filler] * count)

        # Speech rate
        speech_rate = None
        if duration_seconds and duration_seconds > 0:
            speech_rate = (len(words) / duration_seconds) * 60  # words per minute

        # Sentence analysis
        sentences = self._split_sentences(text)
        avg_sentence_length = len(words) / max(len(sentences), 1)

        return {
            "filler_words_count":   filler_count,
            "filler_words_list":    found_fillers,
            "total_words":          len(words),
            "unique_words":         len(set(words)),
            "speech_rate_wpm":      round(speech_rate, 1) if speech_rate else None,
            "sentences":            len(sentences),
            "avg_sentence_length":  round(avg_sentence_length, 1),
        }

    def detect_pauses(self, timestamps: List[Tuple[float, str]]) -> Dict:
        """
        Detect pauses between speech segments.

        Args:
            timestamps: List of (timestamp, text) tuples

        Returns:
            {
                "pause_count": int,
                "avg_pause_duration": float,
                "max_pause_duration": float,
                "pauses": [(start, duration), ...]
            }
        """
        if len(timestamps) < 2:
            return {
                "pause_count": 0,
                "avg_pause_duration": 0.0,
                "max_pause_duration": 0.0,
                "pauses": []
            }

        pauses = []
        for i in range(len(timestamps) - 1):
            current_time = timestamps[i][0]
            next_time = timestamps[i + 1][0]
            pause_duration = next_time - current_time

            # Consider it a pause if > 1 second
            if pause_duration > 1.0:
                pauses.append((current_time, pause_duration))

        if not pauses:
            return {
                "pause_count": 0,
                "avg_pause_duration": 0.0,
                "max_pause_duration": 0.0,
                "pauses": []
            }

        durations = [p[1] for p in pauses]
        return {
            "pause_count":         len(pauses),
            "avg_pause_duration":  round(sum(durations) / len(durations), 2),
            "max_pause_duration":  round(max(durations), 2),
            "pauses":              pauses
        }

    def analyze_voice_confidence(self, amplitude_levels: List[float]) -> Dict:
        """
        Analyze voice confidence from audio amplitude levels.

        Args:
            amplitude_levels: List of audio amplitude measurements (0-1)

        Returns:
            {
                "voice_confidence_score": float (0-100),
                "voice_stability": float (0-100),
                "avg_amplitude": float,
                "amplitude_variance": float
            }
        """
        if not amplitude_levels:
            return {
                "voice_confidence_score": 50.0,
                "voice_stability": 50.0,
                "avg_amplitude": 0.0,
                "amplitude_variance": 0.0
            }

        import statistics

        avg_amp = statistics.mean(amplitude_levels)
        variance = statistics.variance(amplitude_levels) if len(amplitude_levels) > 1 else 0

        # Confidence score: higher average amplitude = more confident
        # Range 0.2-0.8 mapped to 30-100
        confidence_score = min(100, max(30, (avg_amp - 0.2) / 0.6 * 70 + 30))

        # Stability: lower variance = more stable
        # Variance 0-0.1 mapped to 100-30
        stability_score = max(30, 100 - (variance * 700))

        return {
            "voice_confidence_score": round(confidence_score, 1),
            "voice_stability":        round(stability_score, 1),
            "avg_amplitude":          round(avg_amp, 3),
            "amplitude_variance":     round(variance, 4)
        }

    def _tokenize(self, text: str) -> List[str]:
        """Split text into words, removing punctuation."""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [w for w in text.split() if w]

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _empty_result(self) -> Dict:
        return {
            "filler_words_count": 0,
            "filler_words_list": [],
            "total_words": 0,
            "unique_words": 0,
            "speech_rate_wpm": None,
            "sentences": 0,
            "avg_sentence_length": 0.0,
        }