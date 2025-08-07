import os
import httpx
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Optional

# Load environment variables
load_dotenv()
API_KEY = os.getenv("CRELATE_API_KEY")
BASE_URL = "https://app.crelate.com/api3"
PAGE_SIZE = 100

if not API_KEY:
    raise RuntimeError("CRELATE_API_KEY must be set as an environment variable.")

client = httpx.Client(
    base_url=BASE_URL,
    params={"api_key": API_KEY},
    timeout=30.0
)


def get_job_contacts(job_id: str) -> List[dict]:
    """
    Return all contacts associated with the given job.
    """
    contacts, offset, total = [], 0, None
    while True:
        resp = client.get(
            "/contacts",
            params={"job_ids": job_id, "limit": PAGE_SIZE, "offset": offset}
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("Data", [])
        meta = data.get("Metadata", {})
        if total is None:
            total = meta.get("TotalCount")
        if not batch:
            break
        contacts.extend(batch)
        offset += len(batch)
        if len(batch) < PAGE_SIZE or (total and offset >= total):
            break
    return contacts


def get_latest_stage(job_id: str, contact_id: str) -> Optional[str]:
    """
    Fetch the most recent stage for a contact on a job.
    """
    resp = client.get(
        f"/jobs/{job_id}/contacts/history",
        params={"contact_id": contact_id, "limit": 10}
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    history = resp.json().get("Data", [])
    if not history:
        return None
    # sort by the Date field descending
    history.sort(
        key=lambda item: datetime.fromisoformat(item["Date"].rstrip("Z")),
        reverse=True
    )
    return history[0].get("Stage", {}).get("Title")


def download_contact_attachment(contact: dict, output_dir: Path) -> None:
    """
    Download a contact's primary resume into output_dir.
    """
    pa = contact.get("PrimaryDocumentAttachmentId")
    if not pa or not pa.get("Id"):
        return
    aid = pa["Id"]
    name = pa.get("Title", aid)
    resp = client.get(f"/artifacts/{aid}/content", timeout=60.0)
    if resp.status_code != 200:
        return
    dest = output_dir / contact["Id"]
    dest.mkdir(parents=True, exist_ok=True)
    with open(dest / name, "wb") as f:
        f.write(resp.content)


def get_job_documents(job_id: str, limit: int = PAGE_SIZE) -> List[dict]:
    """
    Return all document artifacts attached to a job.
    """
    docs, offset, total = [], 0, None
    while True:
        resp = client.get(
            "/artifacts",
            params={
                "parent_ids": job_id,
                "is_document": True,
                "limit": limit,
                "offset": offset
            }
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("Data", [])
        meta = data.get("Metadata", {})
        if total is None:
            total = meta.get("TotalRecords") or meta.get("TotalCount")
        if not batch:
            break
        docs.extend(batch)
        offset += len(batch)
        if len(batch) < limit or (total and offset >= total):
            break
    return docs


def download_job_documents(job_id: str, output_dir: Path) -> None:
    """
    Download all document artifacts for a job into output_dir.
    """
    docs = get_job_documents(job_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    for art in docs:
        aid = art.get("Id")
        filename = art.get("FileName") or art.get("Name") or aid
        resp = client.get(f"/artifacts/{aid}/content", timeout=60.0)
        if resp.status_code != 200:
            continue
        with open(output_dir / filename, "wb") as f:
            f.write(resp.content)


def process_job(
    job_id: str,
    stage_name: str,
    resume_dir: Path,
    docs_dir: Path
) -> None:
    """
    Download resumes for candidates in the given stage and
    all job documents into their respective folders.
    """
    # resumes
    resume_dir.mkdir(parents=True, exist_ok=True)
    for c in get_job_contacts(job_id):
        if get_latest_stage(job_id, c["Id"]).strip() == stage_name:
            download_contact_attachment(c, resume_dir)

    # documents
    download_job_documents(job_id, docs_dir)

# Usage
# from crelate_client import process_job
# process_job(
#     job_id="...",
#     stage_name="Submitted",
#     resume_dir=Path("resumes"),
#     docs_dir=Path("job_docs")
# )
