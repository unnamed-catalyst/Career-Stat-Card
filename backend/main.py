from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import shutil
from utils import parse_pdf, analyze_resume, parse_response

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), job_description: str = Form("")):
    # Save uploaded file
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Extract and analyze
        resume_text = parse_pdf(temp_path)
        model_response = analyze_resume(resume_text, job_description)
        parsed_stats = parse_response(model_response)

        return JSONResponse(content=parsed_stats)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        os.remove(temp_path)
