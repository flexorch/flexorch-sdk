# flexorch-sdk

Python SDK for the [FlexOrch](https://flexorch.com) API — process documents, build LLM-ready datasets, manage jobs and exports.

## Install

```bash
pip install flexorch-sdk
```

## Quick start

```python
from flexorch_sdk import FlexOrchClient

client = FlexOrchClient("fx_your_key_here")

# Process a document and wait for the pipeline to finish
job = client.process("contract.pdf", locale="tr").wait()

print(job.quality_grade)   # "A"
print(job.quality_score)   # 0.91

# Download the dataset
dataset = job.dataset()
dataset.export("jsonl", path="output.jsonl")
```

## Auth

Pass your API key directly or via environment variable:

```bash
export FLEXORCH_API_KEY=fx_...
```

```python
import os
from flexorch_sdk import FlexOrchClient

client = FlexOrchClient(os.environ["FLEXORCH_API_KEY"])
```

## Resources

```python
# Jobs
client.jobs.list()
client.jobs.get("job-id")

# Datasets
client.datasets.list()
client.datasets.get("dataset-id")

# Usage
usage = client.usage.current()
print(usage.credits_remaining)

# Webhooks
client.webhooks.register("https://your-server.com/hook", events=["dataset.ready"])
client.webhooks.list()
client.webhooks.delete("webhook-id")
```

## Batch processing

```python
jobs = client.process_many(["a.pdf", "b.pdf", "c.pdf"], locale="und")
for job in jobs:
    job.wait()
    print(job.quality_grade)
```

## S3 connector

```python
# Register once, reuse the connector_id
conn = client.connectors.create(
    "Production S3", "s3",
    {"bucket": "my-bucket", "region": "eu-central-1",
     "access_key_id": "AKIA...", "secret_access_key": "..."},
)
result = client.connectors.test(conn.id)
print(result.success, result.latency_ms)

# Import documents directly from S3
jobs = client.process_from_s3(conn.id, ["invoices/inv-001.pdf"], locale="de")
job = jobs[0].wait()

# Export the dataset back to S3
ds = job.dataset()
push = ds.export_to_s3(conn.id, "jsonl", prefix="processed/")
print(push["s3_key"])
```

## Semantic search (Pro+)

```python
# Index a dataset first
ds = client.datasets.get("dataset-id")
ds.index()

# Search across all indexed datasets
results = client.search(
    "invoice payment terms",
    top_k=10,
    filters={"document_type": "invoice", "language": "de"},
)
for r in results:
    print(f"{r.score:.2f}  {r.text[:80]}")
```

## Error handling

```python
from flexorch_sdk import FlexOrchClient, AuthError, QuotaError, JobFailedError

try:
    job = client.process("doc.pdf").wait()
except AuthError:
    print("Invalid API key")
except QuotaError:
    print("Credit quota exceeded")
except JobFailedError as e:
    print(f"Pipeline failed: {e.failure_reason}")
```

## License

MIT
