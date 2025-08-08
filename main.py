import os
import sys
import shutil
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from crelate_client import process_job
from AI_agent import find_best_resumes  # your analyzer

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Sample job and stage from specification ────────────────────────────────────
default_job_id = input("Please enter job code (last part in job URL)") or "29b80d57-280c-414f-b9ea-d4dd080472d1"
default_stage_name = input("Please enter stage name (e.g. \"Good Fit\")")or os.getenv("DEFAULT_STAGE")

# ─── Directories for output ─────────────────────────────────────────────────────
resume_output_dir   = Path("resumes")
document_output_dir = Path("job_documents")


def clear_folder(folder: Path):
    """Delete all files & subfolders under `folder` (but keep the folder itself)."""
    if folder.exists() and folder.is_dir():
        logger.info("Clearing contents of %s", folder)
        for item in folder.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except Exception as e:
                logger.warning("Could not remove %s: %s", item, e)


if __name__ == "__main__":
    # 0) Clear out any old files
    clear_folder(resume_output_dir)
    clear_folder(document_output_dir)

    # 1) Ensure output directories exist
    try:
        resume_output_dir.mkdir(parents=True, exist_ok=True)
        document_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Output folders ready: %s, %s", resume_output_dir, document_output_dir)
    except Exception as e:
        logger.error("Unable to prepare folders: %s", e)
        input("Press Enter to exit...")
        sys.exit(1)

    # 2) Download resumes & job docs
    print("Downloading resumes and job documents...")
    try:
        logger.info("Starting process_job for job %s, stage '%s'", default_job_id, default_stage_name)
        process_job(
            job_id=default_job_id,
            stage_name=default_stage_name,
            resume_dir=resume_output_dir,
            docs_dir=document_output_dir
        )
        logger.info("Download completed successfully.")
        print(f"Resumes downloaded to: {resume_output_dir.resolve()}")
        print(f"Job documents downloaded to: {document_output_dir.resolve()}")
    except Exception as e:
        logger.error("Download failed: %s", e)
        input("Press Enter to exit...")
        sys.exit(1)

    # 3) Score & rank with your AI agent
    try:
        logger.info("Starting resume scoring using AI agent.")
        results = find_best_resumes(
            resumes_folder=resume_output_dir,
            job_docs_folder=document_output_dir
        )
    except Exception as e:
        logger.error("Scoring failed: %s", e)
        input("Press Enter to exit...")
        sys.exit(1)
    else:
        import json
        print("\n=== Resume Match Scores ===")
        print(json.dumps(results, ensure_ascii=False, indent=2))

    # 4) Final prompt
    input("Press Enter to close...")
