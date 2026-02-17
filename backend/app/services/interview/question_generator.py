"""
Question generator service.
Generates personalized interview questions from resume data using gpt-4o-mini.
"""
import json
import re
import httpx

from app.core.config import settings


class QuestionGeneratorService:

    async def generate_questions(
        self,
        job_role: str,
        skills: list = None,
        experience_years: int = None,
        interview_type: str = "job_role",
        num_questions: int = 8
    ) -> list:
        """
        Generate interview questions tailored to the candidate's resume.

        Returns a list of question dicts:
        [
            {
                "question": "Tell me about your experience with Python.",
                "type": "technical",
                "follow_up": "Can you give a specific example?"
            },
            ...
        ]
        """
        if not settings.AZURE_OPENAI_API_KEY:
            return self._default_questions(job_role)

        skills_str = ", ".join(skills[:10]) if skills else "general software skills"
        exp_str    = f"{experience_years} years" if experience_years else "some"

        prompt = f"""
You are an expert interviewer preparing questions for a {job_role} candidate.

Candidate profile:
- Role: {job_role}
- Experience: {exp_str}
- Key skills: {skills_str}
- Interview type: {interview_type}

Generate exactly {num_questions} interview questions.
Mix of: behavioral (40%), technical (40%), situational (20%).

Return ONLY a JSON array:
[
    {{
        "question": "full question text",
        "type": "behavioral|technical|situational",
        "category": "experience|skills|problem-solving|communication|leadership",
        "follow_up": "one follow-up question to dig deeper"
    }}
]

Rules:
- Make questions specific to the candidate's role and skills
- Start with easier questions, get harder toward the end
- Include at least 2 questions about listed skills
- No yes/no questions
- Return ONLY the JSON array
"""

        headers = {
            "api-key": settings.AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json"
        }

        body = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert technical interviewer. Return only valid JSON arrays."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.7   # slightly creative for varied questions
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
            questions = json.loads(content)

            print(f"✅ Generated {len(questions)} questions for {job_role}")
            return questions

        except Exception as e:
            print(f"Question generation failed: {e}")
            return self._default_questions(job_role)

    def _default_questions(self, job_role: str) -> list:
        """Fallback questions when OpenAI is unavailable."""
        return [
            {
                "question": f"Tell me about yourself and your journey to becoming a {job_role}.",
                "type": "behavioral",
                "category": "experience",
                "follow_up": "What specific experience prepared you most for this role?"
            },
            {
                "question": "Describe a challenging technical problem you solved recently.",
                "type": "technical",
                "category": "problem-solving",
                "follow_up": "What would you do differently now?"
            },
            {
                "question": "How do you stay updated with the latest industry trends?",
                "type": "behavioral",
                "category": "skills",
                "follow_up": "Can you give an example of something new you implemented?"
            },
            {
                "question": "Tell me about a time you worked under pressure to meet a deadline.",
                "type": "situational",
                "category": "communication",
                "follow_up": "How did you prioritize your tasks?"
            },
            {
                "question": "Describe your experience working in a team environment.",
                "type": "behavioral",
                "category": "leadership",
                "follow_up": "What role do you usually take in team projects?"
            },
            {
                "question": "What is your greatest professional achievement?",
                "type": "behavioral",
                "category": "experience",
                "follow_up": "What impact did this have on the team or company?"
            },
            {
                "question": "Where do you see yourself in 3 years?",
                "type": "situational",
                "category": "experience",
                "follow_up": "What steps are you taking to get there?"
            },
            {
                "question": "Do you have any questions for us?",
                "type": "behavioral",
                "category": "communication",
                "follow_up": None
            }
        ]
