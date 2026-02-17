"""
Feedback Calculator.
Calculates scores (0-100) for content, communication, and confidence
based on interview metrics and responses.
"""
from app.models.metric import InterviewMetric
from app.models.interview import Interview


class FeedbackCalculator:

    # ── Thresholds ────────────────────────────────────────────────────────────
    # Communication
    FILLER_WORDS_GOOD     = 3    # <= 3 fillers = good
    FILLER_WORDS_POOR     = 10   # >= 10 fillers = poor
    SPEECH_RATE_MIN       = 110  # wpm - too slow
    SPEECH_RATE_MAX       = 160  # wpm - too fast
    PAUSE_GOOD            = 2.0  # seconds avg pause = good
    PAUSE_POOR            = 5.0  # seconds avg pause = poor

    # Confidence (video + audio)
    EYE_CONTACT_GOOD      = 70   # % >= 70 = good
    EYE_CONTACT_POOR      = 40   # % <= 40 = poor
    FIDGETING_GOOD        = 3    # count <= 3 = good
    FIDGETING_POOR        = 10   # count >= 10 = poor
    VOICE_CONFIDENCE_GOOD = 70   # score >= 70 = good
    VOICE_CONFIDENCE_POOR = 40   # score <= 40 = poor

    # Content
    MIN_WORDS_PER_ANSWER  = 30   # good answer has >= 30 words
    MIN_WORDS_POOR        = 10   # poor answer has <= 10 words

    def calculate_all_scores(
        self,
        interview: Interview,
        metric: InterviewMetric = None
    ) -> dict:
        """
        Calculate all three scores and return a complete score dict.

        Returns:
            {
                "content_score":       float,
                "communication_score": float,
                "confidence_score":    float,
                "overall_score":       float,
                "breakdown":           dict   # per-metric details
            }
        """
        responses = interview.responses_given or []
        questions = interview.questions_asked or []

        content_score       = self.calculate_content_score(responses, questions)
        communication_score = self.calculate_communication_score(metric)
        confidence_score    = self.calculate_confidence_score(metric)

        # Weighted overall score
        overall = (
            content_score       * 0.45 +
            communication_score * 0.30 +
            confidence_score    * 0.25
        )

        return {
            "content_score":       round(content_score, 1),
            "communication_score": round(communication_score, 1),
            "confidence_score":    round(confidence_score, 1),
            "overall_score":       round(overall, 1),
            "breakdown":           self._get_breakdown(metric, responses)
        }

    def calculate_content_score(self, responses: list, questions: list) -> float:
        """
        Score based on:
        - Response completeness (word count per answer)
        - Number of questions answered vs total asked
        """
        if not responses:
            return 30.0   # answered nothing

        total_questions  = max(len(questions), 1)
        answered         = len(responses)
        completion_ratio = min(answered / total_questions, 1.0)

        # Average words per answer
        avg_words = sum(
            len(r.get("response", "").split())
            for r in responses
        ) / len(responses)

        # Score word count
        if avg_words >= self.MIN_WORDS_PER_ANSWER:
            word_score = 100.0
        elif avg_words <= self.MIN_WORDS_POOR:
            word_score = 30.0
        else:
            word_score = 30 + (avg_words - self.MIN_WORDS_POOR) / \
                         (self.MIN_WORDS_PER_ANSWER - self.MIN_WORDS_POOR) * 70

        # Blend completion + word score
        return (completion_ratio * 0.4 + (word_score / 100) * 0.6) * 100

    def calculate_communication_score(self, metric: InterviewMetric = None) -> float:
        """
        Score based on filler words, speech rate, pauses.
        Falls back to 70 if no metrics available.
        """
        if not metric:
            return 70.0

        scores = []

        # Filler words score
        fillers = metric.filler_words_count or 0
        if fillers <= self.FILLER_WORDS_GOOD:
            scores.append(100.0)
        elif fillers >= self.FILLER_WORDS_POOR:
            scores.append(30.0)
        else:
            scores.append(
                100 - ((fillers - self.FILLER_WORDS_GOOD) /
                       (self.FILLER_WORDS_POOR - self.FILLER_WORDS_GOOD)) * 70
            )

        # Speech rate score
        wpm = metric.speech_rate_wpm or 0
        if wpm == 0:
            scores.append(70.0)
        elif self.SPEECH_RATE_MIN <= wpm <= self.SPEECH_RATE_MAX:
            scores.append(100.0)
        elif wpm < self.SPEECH_RATE_MIN:
            scores.append(max(30, 100 - (self.SPEECH_RATE_MIN - wpm) * 0.8))
        else:
            scores.append(max(30, 100 - (wpm - self.SPEECH_RATE_MAX) * 0.8))

        # Pause score
        avg_pause = metric.average_pause_duration or 0
        if avg_pause == 0:
            scores.append(70.0)
        elif avg_pause <= self.PAUSE_GOOD:
            scores.append(100.0)
        elif avg_pause >= self.PAUSE_POOR:
            scores.append(40.0)
        else:
            scores.append(
                100 - ((avg_pause - self.PAUSE_GOOD) /
                       (self.PAUSE_POOR - self.PAUSE_GOOD)) * 60
            )

        return sum(scores) / len(scores)

    def calculate_confidence_score(self, metric: InterviewMetric = None) -> float:
        """
        Score based on eye contact, fidgeting, voice confidence.
        Falls back to 70 if no metrics available.
        """
        if not metric:
            return 70.0

        scores = []

        # Eye contact score
        eye = metric.eye_contact_percentage or 0
        if eye >= self.EYE_CONTACT_GOOD:
            scores.append(100.0)
        elif eye <= self.EYE_CONTACT_POOR:
            scores.append(30.0)
        else:
            scores.append(
                30 + ((eye - self.EYE_CONTACT_POOR) /
                      (self.EYE_CONTACT_GOOD - self.EYE_CONTACT_POOR)) * 70
            )

        # Fidgeting score
        fidget = metric.fidgeting_count or 0
        if fidget <= self.FIDGETING_GOOD:
            scores.append(100.0)
        elif fidget >= self.FIDGETING_POOR:
            scores.append(30.0)
        else:
            scores.append(
                100 - ((fidget - self.FIDGETING_GOOD) /
                       (self.FIDGETING_POOR - self.FIDGETING_GOOD)) * 70
            )

        # Voice confidence score
        voice = metric.voice_confidence_score or 0
        if voice == 0:
            scores.append(70.0)
        elif voice >= self.VOICE_CONFIDENCE_GOOD:
            scores.append(100.0)
        elif voice <= self.VOICE_CONFIDENCE_POOR:
            scores.append(30.0)
        else:
            scores.append(
                30 + ((voice - self.VOICE_CONFIDENCE_POOR) /
                      (self.VOICE_CONFIDENCE_GOOD - self.VOICE_CONFIDENCE_POOR)) * 70
            )

        return sum(scores) / len(scores)

    def _get_breakdown(self, metric: InterviewMetric, responses: list) -> dict:
        """Return raw metric values for detailed display."""
        avg_words = 0
        if responses:
            avg_words = sum(
                len(r.get("response", "").split()) for r in responses
            ) / len(responses)

        return {
            "filler_words_count":     metric.filler_words_count     if metric else 0,
            "speech_rate_wpm":        metric.speech_rate_wpm        if metric else 0,
            "average_pause_duration": metric.average_pause_duration if metric else 0,
            "eye_contact_percentage": metric.eye_contact_percentage if metric else 0,
            "fidgeting_count":        metric.fidgeting_count        if metric else 0,
            "voice_confidence_score": metric.voice_confidence_score if metric else 0,
            "avg_words_per_answer":   round(avg_words, 1),
            "total_responses":        len(responses),
        }
