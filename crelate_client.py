import os
import sys
import httpx
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

API_KEY    = os.getenv("CRELATE_API_KEY")
JOB_ID     = "9df1bb64-fa09-466e-a5fa-a4703c87dd08"
BASE_URL   = "https://app.crelate.com/api3"
OUTPUT_DIR = Path("resumes")
PAGE_SIZE  = 100

if not API_KEY:
    print("Error: Set the CRELATE_API_KEY environment variable.", file=sys.stderr)
    sys.exit(1)

client = httpx.Client(
    base_url=BASE_URL,
    params={"api_key": API_KEY},
    timeout=30.0
)

def get_job_contacts(job_id: str):
    contacts, offset, total = [], 0, None
    while True:
        resp = client.get(
            "/contacts",
            params={"job_ids": job_id, "limit": PAGE_SIZE, "offset": offset}
        )
        resp.raise_for_status()
        payload = resp.json()
        batch   = payload.get("Data", [])
        meta    = payload.get("Metadata", {})
        if total is None:
            total = meta.get("TotalCount")
        if not batch:
            break
        contacts.extend(batch)
        offset += len(batch)
        if len(batch) < PAGE_SIZE or (total is not None and offset >= total):
            break
    return contacts

def get_latest_stage(contact_id: str) -> str | None:
    """
    Fetch up to 100 stage-change history entries, sort by Date desc in code,
    and return the most recent Stage Title.
    """
    resp = client.get(
        f"/jobs/{JOB_ID}/contacts/history",
        params={"contact_id": contact_id, "limit": 10}
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    history = resp.json().get("Data", [])
    if not history:
        return None

    # parse and sort
    def parse_date(item):
        return datetime.fromisoformat(item["Date"].rstrip("Z"))
    history.sort(key=parse_date, reverse=True)
    #print(history)
    latest = history[0].get("Stage", {})
    return latest.get("Title")

def download_contact_attachment(contact: dict):
    pa = contact.get("PrimaryDocumentAttachmentId")
    if not pa or not pa.get("Id"):
        print(f"{contact['Id']} – {contact.get('FullName','<no name>')}: no resume")
        return

    aid      = pa["Id"]
    filename = pa.get("Title", aid)
    r        = client.get(f"/artifacts/{aid}/content", timeout=60)
    if r.status_code == 404:
        print(f"{contact['Id']}: artifact {aid} not found")
        return
    r.raise_for_status()

    dest = OUTPUT_DIR / contact["Id"]
    dest.mkdir(parents=True, exist_ok=True)
    with open(dest / filename, "wb") as f:
        f.write(r.content)
    print(f"{contact['Id']} – {contact.get('FullName','<no name>')}: saved {filename}")


def get_job_documents(job_id: str, limit: int = PAGE_SIZE) -> list[dict]:
    """
    Retrieve all document artifacts attached to the specified job.

    Uses the GET /artifacts endpoint with parent_ids=job_id and is_document=true
    to return only document files (excludes images) for that job.

    Args:
        job_id: GUID of the Job record
        limit: page size (max results per call)

    Returns:
        A list of artifact objects with at least Id and FileName keys.
    """
    artifacts: list[dict] = []
    offset = 0
    total_count = None

    while True:
        resp = client.get(
            "/artifacts",
            params={
                "parent_ids": job_id,
                "is_document": True,  # only documents
                "limit": limit,
                "offset": offset
            }
        )
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("Data", [])
        meta  = payload.get("Metadata", {})
        if total_count is None:
            # depending on Crelate version, use TotalRecords or TotalCount
            total_count = meta.get("TotalRecords") or meta.get("TotalCount")
        if not batch:
            break

        artifacts.extend(batch)
        offset += len(batch)
        if len(batch) < limit or (total_count is not None and offset >= total_count):
            break

    return artifacts

def download_job_documents(job_id: str, output_dir: Path = Path("job_documents")) -> None:
    """
    Download all document artifacts attached to a job into a folder.

    Args:
        job_id: GUID of the Job record.
        output_dir: directory where files will be saved (default: job_documents)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    docs = get_job_documents(job_id)
    if not docs:
        print(f"No documents found for job {job_id}.")
        return

    for art in docs:
        art_id = art.get("Id")
        filename = art.get("FileName") or art.get("Name") or art_id
        # fetch file contents
        resp = client.get(f"/artifacts/{art_id}/content", timeout=60.0)
        if resp.status_code == 404:
            print(f"{art_id}: artifact not found")
            continue
        resp.raise_for_status()
        dest = output_dir / filename
        with open(dest, "wb") as f:
            f.write(resp.content)
        print(f"Downloaded {filename}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    contacts = get_job_contacts(JOB_ID)
    if not contacts:
        print(f"No contacts found for job {JOB_ID}.")
        return

    for c in contacts:
        if get_latest_stage(c["Id"]).strip() == "Good Fit":
            download_contact_attachment(c)

if __name__ == "__main__":
    main()
