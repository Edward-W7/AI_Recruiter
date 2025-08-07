from pathlib import Path
import shutil
from crelate_client import process_job
from AI_agent import find_best_resumes  # your analyzer

# Sample job and stage from specification
default_job_id = "29b80d57-280c-414f-b9ea-d4dd080472d1"
default_stage_name = "Good Fit"

# Directories for output
resume_output_dir   = Path("resumes")
document_output_dir = Path("job_documents")

def clear_folder(folder: Path):
    """Delete all files & subfolders under `folder` (but keep the folder itself)."""
    if folder.exists() and folder.is_dir():
        for item in folder.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

if __name__ == "__main__":
    # 0) Clear out any old files
    clear_folder(resume_output_dir)
    clear_folder(document_output_dir)

    # 1) Ensure output directories exist
    resume_output_dir.mkdir(parents=True, exist_ok=True)
    document_output_dir.mkdir(parents=True, exist_ok=True)

    print("Finding Resumes and Job Descriptions...")
    # 2) Download resumes & job docs
    process_job(
        job_id=default_job_id,
        stage_name=default_stage_name,
        resume_dir=resume_output_dir,
        docs_dir=document_output_dir
    )
    print(f"Resumes downloaded to: {resume_output_dir.resolve()}")
    print(f"Job documents downloaded to: {document_output_dir.resolve()}")

    # 3) Score & rank with your AI agent
    try:
        results = find_best_resumes(
            resumes_folder=resume_output_dir,
            job_docs_folder=document_output_dir
        )
    except Exception as e:
        print(f"Error scoring resumes: {e}")
    else:
        import json
        print("\n=== Resume Match Scores ===")
        print(json.dumps(results, ensure_ascii=False, indent=2))
