"""S3 example: register a connector, import documents, export results back to S3."""
import os
from flexorch_sdk import FlexOrchClient, JobFailedError

client = FlexOrchClient(os.environ["FLEXORCH_API_KEY"])

# Register an S3 connector (one-time setup — reuse connector_id afterward)
conn = client.connectors.create(
    "Production S3",
    "s3",
    {
        "bucket": os.environ["S3_BUCKET"],
        "region": os.environ.get("AWS_REGION", "eu-central-1"),
        "access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
        "secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
    },
)
print(f"Connector created: {conn.id}")

# Verify connectivity
result = client.connectors.test(conn.id)
if not result.success:
    raise RuntimeError(f"Connector test failed: {result.message}")
print(f"Connection OK ({result.latency_ms} ms)")

# Import documents from S3 and process them
keys = ["invoices/2026/inv-001.pdf", "invoices/2026/inv-002.pdf"]
jobs = client.process_from_s3(conn.id, keys, locale="de")

for job in jobs:
    try:
        job.wait(timeout=300)
        ds = job.dataset()
        if ds:
            # Export result back to S3
            push = ds.export_to_s3(conn.id, "jsonl", prefix="processed/")
            print(f"  ✓ {ds.name} → s3://{push['s3_key']} ({push['size_bytes']} bytes)")
    except JobFailedError as e:
        print(f"  ✗ job {e.job_id} failed: {e.failure_reason}")
