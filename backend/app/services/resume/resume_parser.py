"""
Resume parser service.
Extracts text from PDF using PyMuPDF, then parses with gpt-4o-mini.
"""
import json
import re
import httpx
import fitz       # PyMuPDF
import pdfplumber
import io

from app.core.config import settings


class ResumeParserService:

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """
        Extract text using PyMuPDF first (better spacing),
        fall back to pdfplumber if text looks garbled.
        """
        text = self._extract_with_pymupdf(file_bytes)

        if not text or self._is_garbled(text):
            text = self._extract_with_pdfplumber(file_bytes)

        return text.strip()

    def _extract_with_pymupdf(self, file_bytes: bytes) -> str:
        try:
            doc  = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
            return text
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
            return ""

    def _extract_with_pdfplumber(self, file_bytes: bytes) -> str:
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
            return ""

    def _is_garbled(self, text: str) -> bool:
        """Check if words are merged together (avg word length > 12)."""
        words = text.split()
        if not words:
            return True
        return (sum(len(w) for w in words) / len(words)) > 12

    async def parse_with_gpt(self, resume_text: str) -> dict:
        """
        Parse resume using gpt-4o-mini via chat completions API.
        Uses settings.chat_api_url which points to AZURE_OPENAI_CHAT_DEPLOYMENT_NAME.
        """
        if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
            print("OpenAI not configured — using basic parser.")
            return self._basic_parse(resume_text)

        prompt = f"""
Parse this resume and extract structured information.
The text may have formatting issues (merged words) — interpret it carefully.

Return ONLY a valid JSON object:
{{
    "job_role": "most recent job title (e.g. Machine Learning Engineer)",
    "experience_years": <integer or null>,
    "skills": ["skill1", "skill2"],
    "education": [
        {{"degree": "...", "institution": "...", "year": "..."}}
    ],
    "work_history": [
        {{"title": "...", "company": "...", "duration": "...", "description": "..."}}
    ],
    "certifications": ["cert1"],
    "summary": "2-sentence professional summary"
}}

Rules:
- job_role: use the most recent job title, NOT a bullet point description
- If text has merged words like "MachineLearningEngineer", split them correctly
- Return ONLY JSON, no markdown, no explanation

Resume:
{resume_text[:4000]}
"""

        headers = {
            "api-key": settings.AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json"
        }

        body = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise resume parser. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1200,
            "temperature": 0.1
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    settings.chat_api_url,   # ← uses gpt-4o-mini deployment
                    headers=headers,
                    json=body
                )
                response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]

            # Strip markdown fences if GPT adds them
            content = re.sub(r"```json|```", "", content).strip()

            parsed = json.loads(content)
            print(f"✅ GPT parsed resume: job_role={parsed.get('job_role')}")
            return parsed

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return self._basic_parse(resume_text)
        except Exception as e:
            print(f"GPT parsing failed: {e}")
            return self._basic_parse(resume_text)

    def _basic_parse(self, text: str) -> dict:
        """Fallback heuristic parser when OpenAI is unavailable."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        skill_keywords = [
            "python", "javascript", "typescript", "react", "node", "sql",
            "java", "c++", "c#", "aws", "azure", "docker", "kubernetes",
            "machine learning", "deep learning", "fastapi", "django", "flask",
            "mongodb", "postgresql", "redis", "git", "linux", "html", "css",
            "next.js", "tensorflow", "pytorch", "scikit-learn", "pandas",
            "numpy", "spark", "kafka", "graphql"
        ]
        text_lower  = text.lower()
        found_skills = [s for s in skill_keywords if s in text_lower]

        job_role = None
        role_pattern = re.compile(
            r'\b(machine learning|software|data|backend|frontend|full.?stack|'
            r'devops|cloud|ml|ai|nlp)\s+'
            r'(engineer|developer|scientist|analyst|architect|intern|lead)\b',
            re.IGNORECASE
        )
        for line in lines[:20]:
            match = role_pattern.search(line)
            if match:
                job_role = match.group(0).title()
                break

        exp_match = re.search(
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            text, re.IGNORECASE
        )

        return {
            "job_role":         job_role or "Software Engineer",
            "experience_years": int(exp_match.group(1)) if exp_match else None,
            "skills":           found_skills,
            "education":        [],
            "work_history":     [],
            "certifications":   [],
            "summary":          " ".join(lines[:3]) if lines else ""
        }