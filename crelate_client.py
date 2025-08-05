import os
import sys
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY    = os.getenv("CRELATE_API_KEY")
JOB_ID     = "9df1bb64-fa09-466e-a5fa-a4703c87dd08"
BASE_URL   = "https://app.crelate.com/api3"
OUTPUT_DIR = Path("resumes")
PAGE_SIZE  = 100  # Number of contacts to fetch per request, increase as needed

if not API_KEY:
    print("Error: Set the CRELATE_API_KEY environment variable.", file=sys.stderr)
    sys.exit(1)

# HTTPX client with query-param auth for v3
client = httpx.Client(
    base_url=BASE_URL,
    params={"api_key": API_KEY},
    timeout=30.0
)

def get_job_contacts(job_id):
    """Fetch every contact pipelined into a job via GET /contacts?job_ids=... using OData $top & $skip."""
    contacts = []
    skip = 0

    while True:
        resp = client.get(
            "/contacts",
            params={
                "job_ids": job_id,
                "$top": PAGE_SIZE,
                "$skip": skip
            }
        )
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("Data", [])
        print(f"Fetched {len(batch)} contacts (skip={skip})")
        if not batch:
            break

        contacts.extend(batch)
        # If this batch is smaller than PAGE_SIZE, we've reached the end
        if len(batch) < PAGE_SIZE:
            break

        skip += PAGE_SIZE

    print(f"Total contacts fetched for job {job_id}: {len(contacts)}")
    return contacts


def download_contact_attachment(contact):
    """Download the primary resume attachment for a contact via GET /artifacts/{artifactId}/content."""
    pa = contact.get("PrimaryDocumentAttachmentId")
    if not pa or not pa.get("Id"):
        print(f"{contact.get('Id')} – {contact.get('FullName') or contact.get('Name')}: no primary document.")
        return

    contact_id = contact.get("Id")
    artifact_id = pa["Id"]
    filename = pa.get("Title") or f"{artifact_id}"
    print(f"{contact_id} – {contact.get('FullName') or contact.get('Name')}: downloading {filename} …")

    # Use artifacts content endpoint
    resp = client.get(f"/artifacts/{artifact_id}/content", timeout=60.0)
    if resp.status_code == 404:
        print(f"  → Artifact {artifact_id} not found (404).")
        return
    resp.raise_for_status()

    dest = OUTPUT_DIR / contact_id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / filename
    with open(path, "wb") as f:
        f.write(resp.content)
    print(f"  ✔ Saved {filename} for contact {contact_id}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    contacts = get_job_contacts(JOB_ID)
    if not contacts:
        print(f"No contacts found for job {JOB_ID}.")
        return

    for contact in contacts:
        download_contact_attachment(contact)

if __name__ == "__main__":
    main()
