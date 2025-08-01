import os
import sys
import httpx
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configuration
JOB_ID     = "9df1bb64-fa09-466e-a5fa-a4703c87dd08"
API_KEY    = os.getenv("CRELATE_API_KEY")
BASE_URL   = "https://app.crelate.com/api/pub/v1"
OUTPUT_DIR = Path("resumes")

if not API_KEY:
    print("Error: Set the CRELATE_API_KEY environment variable.", file=sys.stderr)
    sys.exit(1)

# Use query-param auth for v1
client = httpx.Client(base_url=BASE_URL, params={"api_key": API_KEY}, timeout=30)

def get_applications(job_id):
    """Fetch up to 100 filtered applications via the jobs/{jobId}/applications endpoint."""
    resp = client.get(
        f"/jobs/{job_id}/applications",
        params={"take": 100}
    )
    resp.raise_for_status()
    print(f"Fetched applications from: {resp.request.url}")
    data = resp.json()
    # Debug full payload
    print("Full response JSON:")
    print(json.dumps(data, indent=2))
    return data.get("Data", [])

def get_primary_attachment(app_id):
    """Fetch primary resume attachment metadata for an application via v1."""
    resp = client.get(f"/applications/{app_id}")
    resp.raise_for_status()
    app = resp.json().get("Data", {})
    print(f"Fetched application {app_id}, data:")
    print(json.dumps(app, indent=2))
    aid  = app.get("PrimaryDocumentAttachment_Id")
    name = app.get("PrimaryDocumentAttachment_Name")
    if aid and name:
        return {"Id": aid, "FileName": name}
    return None

def download_attachment(app_id, attachment):
    """Download a resume file using the v1 attachments endpoint."""
    attach_id = attachment["Id"]
    filename  = attachment.get("FileName", f"{attach_id}.pdf")
    resp = client.get(f"/applications/{app_id}/attachments/{attach_id}")
    print(f"Downloading from: {resp.request.url}")
    if resp.status_code == 404:
        print("404: Attachment not found. Check if the ID is correct or use /attachments/{attach_id}/content.")
        return
    resp.raise_for_status()
    dest = OUTPUT_DIR / app_id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / filename
    with open(path, "wb") as f:
        f.write(resp.content)
    print(f"Saved resume for {app_id}: {path}")

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    apps = get_applications(JOB_ID)
    if not apps:
        print(f"No applications found for job {JOB_ID}.")
        return
    for app in apps:
        app_id = app.get("Id")
        if not app_id:
            continue
        attachment = get_primary_attachment(app_id)
        if not attachment:
            print(f"No primary resume for {app_id}.")
            continue
        download_attachment(app_id, attachment)

if __name__ == "__main__":
    main()
