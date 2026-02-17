"""
GPT Feedback Generator.
Uses gpt-4o-mini to generate detailed narrative feedback
and improvement suggestions from interview data.
"""
import json
import re
import httpx

from app.core.config import settings


class GPTFeedbackGenerator:

    async def generate(
        self,
        job_role: str,
        scores: dict,
        what_went_right: list,
        what_went_wrong: list,
        questions_asked: list,
        responses: list
    ) -> dict:
        """
        Generate detailed narrative feedback using gpt-4o-mini.

        Returns:
            {
                "detailed_feedback":       str,
                "improvement_suggestions": [str, ...]
            }
        """
        if not settings.AZURE_OPENAI_API_KEY:
            return self._default_feedback(scores)

        # Build summary of Q&A for GPT
        qa_summary = ""
        for i, q in enumerate(questions_asked[:5]):  # limit to 5 for token savings
            response = ""
            if i < len(responses):
                response = responses[i].get("response", "")[:200]
            qa_summary += f"\nQ{i+1}: {q}\nA{i+1}: {response}\n"

        prompt = f"""
You are an expert interview coach analyzing a mock interview.

Candidate role: {job_role}
Overall score: {scores.get('overall_score', 0)}/100
Content score: {scores.get('content_score', 0)}/100
Communication score: {scores.get('communication_score', 0)}/100
Confidence score: {scores.get('confidence_score', 0)}/100

What went well:
{json.dumps([x['message'] for x in what_went_right], indent=2)}

What needs improvement:
{json.dumps([x['message'] for x in what_went_wrong], indent=2)}

Sample Q&A from the interview:
{qa_summary}

Write a constructive performance review with:
1. detailed_feedback: 3-4 sentences of honest, encouraging feedback referencing specific scores
2. improvement_suggestions: exactly 4 actionable tips to improve next time

Return ONLY valid JSON:
{{
    "detailed_feedback": "...",
    "improvement_suggestions": ["tip1", "tip2", "tip3", "tip4"]
}}
"""

        headers = {
            "api-key": settings.AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json"
        }

        body = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a supportive interview coach. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 600,
            "temperature": 0.6
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    settings.chat_api_url,
                    headers=headers,
                    json=body
                )
                response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]
            content = re.sub(r"```json|```", "", content).strip()
            result  = json.loads(content)

            print(f"✅ GPT feedback generated for {job_role}")
            return result

        except Exception as e:
            print(f"GPT feedback generation failed: {e}")
            return self._default_feedback(scores)

    def _default_feedback(self, scores: dict) -> dict:
        """Fallback feedback when OpenAI is unavailable."""
        overall = scores.get("overall_score", 50)

        if overall >= 80:
            feedback = (
                "Excellent performance! You demonstrated strong communication skills "
                "and provided thorough, well-structured answers. Your confidence came "
                "through clearly. Keep up the great work and continue practicing."
            )
        elif overall >= 60:
            feedback = (
                "Good effort overall. You showed solid foundational skills but there "
                "is room to improve answer depth and communication clarity. Focus on "
                "structuring your responses using the STAR method for better results."
            )
        else:
            feedback = (
                "This was a good practice session. Your responses need more depth "
                "and confidence. Focus on preparation — research common questions for "
                "your target role and practice answering them out loud regularly."
            )

        return {
            "detailed_feedback": feedback,
            "improvement_suggestions": [
                "Use the STAR method (Situation, Task, Action, Result) for behavioral questions",
                "Practice reducing filler words by pausing briefly instead of saying 'um' or 'uh'",
                "Maintain eye contact with the camera to project confidence",
                "Prepare 2-3 detailed examples from your experience for common question types"
            ]
        }
