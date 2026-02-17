"""
Feedback Categorizer.
Auto-categorizes metrics into "What Went Right" and "What Went Wrong"
based on thresholds. No GPT needed for this — pure rule-based logic.
"""


class FeedbackCategorizer:

    def categorize(self, scores: dict, breakdown: dict) -> dict:
        """
        Compare each metric against thresholds and sort into
        what_went_right / what_went_wrong lists.

        Returns:
            {
                "what_went_right": [ {"metric": ..., "value": ..., "message": ...} ],
                "what_went_wrong": [ {"metric": ..., "value": ..., "message": ...} ],
                "strengths":       [str, ...],
                "weaknesses":      [str, ...]
            }
        """
        went_right  = []
        went_wrong  = []

        # ── Communication checks ──────────────────────────────────────────────
        fillers = breakdown.get("filler_words_count", 0)
        if fillers <= 3:
            went_right.append({
                "metric":   "Filler Words",
                "value":    fillers,
                "message":  f"Only {fillers} filler words — very clean speech!"
            })
        elif fillers >= 8:
            went_wrong.append({
                "metric":   "Filler Words",
                "value":    fillers,
                "message":  f"Used {fillers} filler words (um, uh, like). Practice pausing instead."
            })

        wpm = breakdown.get("speech_rate_wpm", 0)
        if wpm > 0:
            if 110 <= wpm <= 160:
                went_right.append({
                    "metric":   "Speech Rate",
                    "value":    f"{wpm} wpm",
                    "message":  f"Great pace at {wpm} wpm — easy to follow."
                })
            elif wpm < 100:
                went_wrong.append({
                    "metric":   "Speech Rate",
                    "value":    f"{wpm} wpm",
                    "message":  f"Speaking too slowly at {wpm} wpm. Aim for 120-150 wpm."
                })
            elif wpm > 170:
                went_wrong.append({
                    "metric":   "Speech Rate",
                    "value":    f"{wpm} wpm",
                    "message":  f"Speaking too fast at {wpm} wpm. Slow down to 120-150 wpm."
                })

        pause = breakdown.get("average_pause_duration", 0)
        if pause > 0:
            if pause <= 2.0:
                went_right.append({
                    "metric":   "Pauses",
                    "value":    f"{pause:.1f}s avg",
                    "message":  "Short, confident pauses between answers."
                })
            elif pause >= 5.0:
                went_wrong.append({
                    "metric":   "Pauses",
                    "value":    f"{pause:.1f}s avg",
                    "message":  f"Long pauses averaging {pause:.1f}s. Prepare answers in advance."
                })

        # ── Confidence checks ─────────────────────────────────────────────────
        eye = breakdown.get("eye_contact_percentage", 0)
        if eye >= 70:
            went_right.append({
                "metric":   "Eye Contact",
                "value":    f"{eye:.0f}%",
                "message":  f"Excellent eye contact at {eye:.0f}% — shows confidence!"
            })
        elif eye <= 40 and eye > 0:
            went_wrong.append({
                "metric":   "Eye Contact",
                "value":    f"{eye:.0f}%",
                "message":  f"Low eye contact at {eye:.0f}%. Look directly at the camera."
            })

        fidget = breakdown.get("fidgeting_count", 0)
        if fidget <= 3:
            went_right.append({
                "metric":   "Body Language",
                "value":    f"{fidget} movements",
                "message":  "Calm and composed body language throughout."
            })
        elif fidget >= 8:
            went_wrong.append({
                "metric":   "Body Language",
                "value":    f"{fidget} movements",
                "message":  f"Excessive movement detected ({fidget} times). Try to stay still."
            })

        voice = breakdown.get("voice_confidence_score", 0)
        if voice >= 70:
            went_right.append({
                "metric":   "Voice Confidence",
                "value":    f"{voice:.0f}/100",
                "message":  "Voice sounds confident and steady."
            })
        elif 0 < voice <= 40:
            went_wrong.append({
                "metric":   "Voice Confidence",
                "value":    f"{voice:.0f}/100",
                "message":  "Voice sounds hesitant. Practice speaking with more conviction."
            })

        # ── Content checks ────────────────────────────────────────────────────
        avg_words = breakdown.get("avg_words_per_answer", 0)
        if avg_words >= 40:
            went_right.append({
                "metric":   "Answer Depth",
                "value":    f"{avg_words:.0f} words avg",
                "message":  f"Detailed answers averaging {avg_words:.0f} words — thorough responses!"
            })
        elif avg_words <= 15 and avg_words > 0:
            went_wrong.append({
                "metric":   "Answer Depth",
                "value":    f"{avg_words:.0f} words avg",
                "message":  f"Short answers averaging {avg_words:.0f} words. Elaborate more using STAR method."
            })

        total_responses = breakdown.get("total_responses", 0)
        if total_responses >= 7:
            went_right.append({
                "metric":   "Completion",
                "value":    f"{total_responses} questions",
                "message":  f"Answered {total_responses} questions — great endurance!"
            })
        elif total_responses <= 3:
            went_wrong.append({
                "metric":   "Completion",
                "value":    f"{total_responses} questions",
                "message":  f"Only answered {total_responses} questions. Try to complete the full interview."
            })

        # ── Score-level checks ────────────────────────────────────────────────
        if scores.get("communication_score", 0) >= 80:
            went_right.append({
                "metric":   "Overall Communication",
                "value":    f"{scores['communication_score']}/100",
                "message":  "Excellent communication throughout the interview."
            })

        if scores.get("confidence_score", 0) >= 80:
            went_right.append({
                "metric":   "Overall Confidence",
                "value":    f"{scores['confidence_score']}/100",
                "message":  "Projected strong confidence and presence."
            })

        if scores.get("content_score", 0) < 50:
            went_wrong.append({
                "metric":   "Overall Content",
                "value":    f"{scores.get('content_score', 0)}/100",
                "message":  "Answers lacked depth. Use the STAR method: Situation, Task, Action, Result."
            })

        # ── Summarize strengths / weaknesses as plain strings ─────────────────
        strengths  = [item["message"] for item in went_right]
        weaknesses = [item["message"] for item in went_wrong]

        return {
            "what_went_right": went_right,
            "what_went_wrong": went_wrong,
            "strengths":       strengths,
            "weaknesses":      weaknesses
        }
