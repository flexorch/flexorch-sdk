"""Batch example: process multiple documents and collect datasets."""
import os
from pathlib import Path
from flexorch_sdk import FlexOrchClient, JobFailedError

client = FlexOrchClient(os.environ["FLEXORCH_API_KEY"])

files = list(Path("documents/").glob("*.pdf"))
print(f"Processing {len(files)} files...")

jobs = client.process_many(files, locale="und")

for job in jobs:
    try:
        job.wait(timeout=300)
        ds = job.dataset()
        if ds:
            ds.export("jsonl", path=f"output/{ds.slug}.jsonl")
            print(f"  ✓ {ds.name} — {ds.row_count} rows (grade {job.quality_grade})")
    except JobFailedError as e:
        print(f"  ✗ job {e.job_id} failed: {e.failure_reason}")
