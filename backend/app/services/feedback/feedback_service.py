"""
Feedback Service.
Orchestrates the full feedback pipeline:
Calculate scores → Categorize metrics → Generate GPT narrative → Save to DB
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.interview import Interview, InterviewStatus
from app.models.feedback import Feedback
from app.models.metric import InterviewMetric
from app.services.feedback.feedback_calculator import FeedbackCalculator
from app.services.feedback.feedback_categorizer import FeedbackCategorizer
from app.services.feedback.feedback_generator import GPTFeedbackGenerator


class FeedbackService:

    def __init__(self):
        self.calculator  = FeedbackCalculator()
        self.categorizer = FeedbackCategorizer()
        self.generator   = GPTFeedbackGenerator()

    async def generate_feedback(
        self,
        db: Session,
        interview_id: int,
        user_id: int
    ) -> Feedback:
        """
        Full feedback pipeline for a completed interview.

        1. Load interview + metrics from DB
        2. Calculate scores
        3. Categorize into what went right / wrong
        4. Generate GPT narrative
        5. Save Feedback to DB
        6. Return Feedback object
        """
        # ── Load interview ────────────────────────────────────────────────────
        interview = (
            db.query(Interview)
            .filter(
                Interview.id      == interview_id,
                Interview.user_id == user_id
            )
            .first()
        )

        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )

        if interview.status != InterviewStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Interview is not completed yet. Status: {interview.status}"
            )

        # Return existing feedback if already generated
        if interview.feedback:
            return interview.feedback

        # ── Load metrics ──────────────────────────────────────────────────────
        metric = (
            db.query(InterviewMetric)
            .filter(InterviewMetric.interview_id == interview_id)
            .order_by(InterviewMetric.recorded_at.desc())
            .first()
        )

        # ── Step 1: Calculate scores ──────────────────────────────────────────
        scores = self.calculator.calculate_all_scores(interview, metric)

        # ── Step 2: Categorize metrics ────────────────────────────────────────
        categories = self.categorizer.categorize(scores, scores["breakdown"])

        # ── Step 3: Generate GPT narrative ────────────────────────────────────
        gpt_result = await self.generator.generate(
            job_role        = interview.job_role or "Software Engineer",
            scores          = scores,
            what_went_right = categories["what_went_right"],
            what_went_wrong = categories["what_went_wrong"],
            questions_asked = interview.questions_asked or [],
            responses       = interview.responses_given or []
        )

        # ── Step 4: Save to database ──────────────────────────────────────────
        feedback = Feedback(
            interview_id            = interview_id,
            content_score           = scores["content_score"],
            communication_score     = scores["communication_score"],
            confidence_score        = scores["confidence_score"],
            overall_score           = scores["overall_score"],
            strengths               = categories["strengths"],
            weaknesses              = categories["weaknesses"],
            what_went_right         = categories["what_went_right"],
            what_went_wrong         = categories["what_went_wrong"],
            detailed_feedback       = gpt_result.get("detailed_feedback"),
            improvement_suggestions = gpt_result.get("improvement_suggestions", [])
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        print(f"✅ Feedback generated for interview {interview_id} — overall: {scores['overall_score']}")
        return feedback

    def get_feedback(self, db: Session, interview_id: int, user_id: int) -> Feedback:
        """Retrieve existing feedback for an interview."""
        interview = (
            db.query(Interview)
            .filter(
                Interview.id      == interview_id,
                Interview.user_id == user_id
            )
            .first()
        )

        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )

        if not interview.feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not yet generated. Complete the interview first."
            )

        return interview.feedback
