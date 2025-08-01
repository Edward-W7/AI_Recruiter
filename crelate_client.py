import os
import sys
import httpx
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
# Configuration
JOB_ID = "9df1bb64-fa09-466e-a5fa-a4703c87dd08"
GROUP_NAME = "New00"
API_KEY = os.getenv("CRELATE_API_KEY")
BASE_URL = "https://app.crelate.com/api3"
OUTPUT_DIR = Path("resumes")

if not API_KEY:
    print("Error: Set the CRELATE_API_KEY environment variable.", file=sys.stderr)
    sys.exit(1)

client = httpx.Client(base_url=BASE_URL, params={"api_key": API_KEY}, timeout=30)

def get_applications(job_id):
    """Fetch all applications for a given job."""
    resp = client.get("/applications", params={"jobId": job_id})
    resp.raise_for_status()
    return resp.json().get("Data", [])

def filter_by_group(applications, group_name):
    """Filter applications by contact group membership, always fetching full contact."""
    filtered = []
    for app in applications:
        # Always fetch the contact record via ContactId
        contact_id = app.get("ContactId", {}).get("Id")
        contact = {}
        if contact_id:
            c_resp = client.get(f"/contacts/{contact_id}")
            c_resp.raise_for_status()
            contact = c_resp.json().get("Data", {}) or {}
        # Extract groups safely
        groups = contact.get("Groups", []) or []
        # Match by Group Title
        if any(g.get("Title") == group_name for g in groups):
            filtered.append(app)
    return filtered

def get_resume_documents(application_id):
    """Fetch all document metadata for an application and filter for resumes."""
    resp = client.get(f"/applications/{application_id}/documents")
    resp.raise_for_status()
    docs = resp.json().get("Data", [])
    return [d for d in docs if d.get("DocumentType") == "Resume"]

def download_file(application_id, document):
    """Download a single resume file and save it locally."""
    doc_id = document["Id"]
    filename = document.get("FileName", f"{doc_id}.pdf")
    resp = client.get(f"/applications/{application_id}/documents/{doc_id}/file")
    resp.raise_for_status()
    dest = OUTPUT_DIR / application_id
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / filename
    with open(file_path, "wb") as f:
        f.write(resp.content)
    print(f"Saved resume for {application_id}: {file_path}")

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    applications = get_applications(JOB_ID)
    applications = filter_by_group(applications, GROUP_NAME)
    if not applications:
        print(f"No applications found in group '{GROUP_NAME}' for job {JOB_ID}.")
        return
    for app in applications:
        aid = app["Id"]
        resumes = get_resume_documents(aid)
        if not resumes:
            print(f"No resumes found for application {aid}.")
            continue
        for doc in resumes:
            download_file(aid, doc)

if __name__ == "__main__":
    main()
