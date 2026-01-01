import fitz  # PyMuPDF
import os
import json
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def parse_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()

    return text


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    else:
        return {"error": "Could not extract JSON from model response"}


def analyze_resume(
    text: str,
    job_description: str = "No job description, just mention the job title that best matches their skills",
) -> dict:
    prompt = f"""
You are an AI career assistant. Analyze the following resume based on the job description/title and return scores for the following much like FIFA card stats, scale the stats based on years of experience as well:
Make sure you fit the person's stats to the skills of the job not the job specifics. E.g.: An ML engineer who has worked in the finance industry their whole career is still highly rated for a job description in the automotive industry even though they never worked in the automotive industry.
The minimum a stat can be is 45, and the max is 99. Scale them to be realistic based on their experience, e.g.: a fresh graduate without any experience isn't realistically in the 90s.
Scale it as such:
0-2 years of experience: 0.8x
2-5 years of experience: 0.85x
5-10 years of experience: 0.9x
10+ years of experience: 1x
If no job description or title is given, just mention the job title that best matches their skills

- Technical Proficiency
- Problem Solving
- Communication
- Domain Fit
- Initiative & Impact
- Adaptability

- And then an Overall score that takes the above 6 into account

Format it as
[Name] - [Job Title]

**[Experience] - [Just the range of the years of experience like the scale above]**

**[Stat name] - [Score]**
[One line explanation for why]

**[Overall Score] - [Score]**
[One line summary of scoring]

Resume:
{text}

Job Description:
{job_description}
"""
    response = client.models.generate_content(model="gemini-flash", contents=prompt)
    try:
        return response.text
    except json.JSONDecodeError:
        return {"error": "Model response could not be parsed"}


def parse_response(text):
    lines = text.strip().splitlines()
    name = None
    role = None
    experience = None
    scores = {}
    explanations = {}

    # First line: "Nawaf Nazeer - Machine Learning Engineer"
    if "-" in lines[0]:
        name_part, role_part = lines[0].split(" - ", 1)
        name = name_part.strip()
        role = role_part.strip()

    current_category = None
    for i, line in enumerate(lines):
        line = line.strip()

        # Match Experience
        if line.startswith("**Experience"):
            match = re.search(r"\*\*Experience - (.*?)\*\*", line)
            if match:
                experience = match.group(1).strip()

        # Match **[Category] - [Score]**
        elif line.startswith("**") and " - " in line:
            match = re.search(r"\*\*(.*?) - (\d+)\*\*", line)
            if match:
                current_category = match.group(1).strip()
                score = int(match.group(2))
                scores[current_category] = score

                # Grab explanation from next line if available
                if i + 1 < len(lines):
                    explanations[current_category] = lines[i + 1].strip()

    return {
        "name": name,
        "target_role": role,
        "experience": experience,
        "overall_score": scores.get("Overall Score"),
        "scores": scores,
        "explanations": explanations,
    }
