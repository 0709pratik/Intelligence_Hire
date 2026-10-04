import os
import json
from google import genai

# Set this in your terminal before running the server:
# Windows (cmd):  set GEMINI_API_KEY=your_key_here
# Mac/Linux:      export GEMINI_API_KEY=your_key_here
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_NAME = "gemini-3.8-flash"


def _clean_json_response(text: str) -> str:
    """Gemini sometimes wraps JSON in ```json ... ``` - strip that off."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.removeprefix("json").strip()
    return cleaned


def structure_resume(raw_text: str) -> dict:
    """Turns messy resume text into clean JSON: skills, projects, experience."""
    prompt = f"""
You are extracting structured data from a resume.
Return ONLY valid JSON, no extra text, no markdown fences, in this exact shape:
{{
  "skills": ["skill1", "skill2"],
  "projects": [{{"title": "...", "description": "..."}}],
  "experience": [{{"role": "...", "company": "...", "description": "..."}}]
}}

Resume text:
{raw_text}
"""
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return json.loads(_clean_json_response(response.text))


def generate_questions(parsed_resume: dict, job_title: str, num_questions: int = 5) -> list[dict]:
    """Generates resume-grounded interview questions for a given job role."""
    prompt = f"""
You are an interviewer preparing questions for a candidate applying to: {job_title}

Candidate's resume data (JSON):
{json.dumps(parsed_resume)}

Generate {num_questions} interview questions. Mix technical and behavioral questions.
Each question MUST reference a specific skill, project, or experience from the resume above
— do not ask generic questions that could apply to anyone.

Return ONLY valid JSON, no extra text, as a list in this exact shape:
[
  {{"question_text": "...", "source_context": "the specific resume detail this is based on", "question_type": "technical or behavioral", "difficulty": "easy or medium or hard"}}
]
"""
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return json.loads(_clean_json_response(response.text))
