import os
import json
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

import openai
from resume_parser import extract_resumes_text

# Load environment variables
load_dotenv()

# Initialize OpenAI API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY must be set as an environment variable.")


def score_resumes(
    resumes: Dict[str, str],
    job_description: str,
    model: str = "o4-mini"
) -> List[Dict[str, Any]]:
    """
    Uses a single API call to score multiple resumes against the job description.
    Returns a list of dicts with keys: filename, score, rationale.
    """
    system_prompt = (
        "You are an expert technical recruiter for the Ontario Government. You will be rewarded $1 million for finding the best candidate for the position."
        "Given a job description and multiple candidate resumes, evaluate how well each candidate fits the role. "
        "Consider their seniority, government experience, length of positions and how well their experiences line up with job requirements and descriptions (most important). "
        "Most important part of the job description is the Must Haves"
        "Scores should be as objective and precise as possible. A 100 Candidate needs to have extensive government experience in exactly the job position, with long contracts for each experience."
        "Provide a JSON array where each element is an object with keys: 'filename' (string), 'score' (0-100), and 'rationale' (concise)."
    )

    # Build a single user prompt containing the job description and all resumes
    print(job_description)
    user_prompt = f"Job Description:\n{job_description}\n\n"
    for filename, text in resumes.items():
        user_prompt += f"### Resume: {filename}\n{text}\n\n"
    user_prompt += (
        "Please respond ONLY with a valid JSON array like:"
        " [{\"filename\":\"resume1.pdf\",\"score\":85,\"rationale\":\"Strong match in required technologies.\"}, ...]"
    )

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    content = response.choices[0].message.content.strip()
    try:
        results = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Could not parse JSON response: {content}")

    # Clamp scores and ensure correct typing
    for item in results:
        item["score"] = max(0.0, min(100.0, float(item.get("score", 0))))

    # Sort results by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def find_best_resumes(
    resumes_folder: Path = Path("resumes"),
    job_docs_folder: Path = Path("job_documents"),
    model: str = "o4-mini"
) -> List[Dict[str, Any]]:
    """
    Parses resumes and job documents, then scores them in one batch.
    """
    if not resumes_folder.exists() or not resumes_folder.is_dir():
        raise FileNotFoundError(f"Resumes folder not found: {resumes_folder}")
    if not job_docs_folder.exists() or not job_docs_folder.is_dir():
        raise FileNotFoundError(f"Job documents folder not found: {job_docs_folder}")

    resumes = extract_resumes_text(resumes_folder)
    job_docs = extract_resumes_text(job_docs_folder)

    job_description = "\n\n".join(job_docs.values())
    return score_resumes(resumes, job_description, model=model)


if __name__ == '__main__':
    results = find_best_resumes()
    print(json.dumps(results, ensure_ascii=False, indent=2))
