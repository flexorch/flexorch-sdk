# flexorch-sdk

[![PyPI](https://img.shields.io/pypi/v/flexorch-sdk)](https://pypi.org/project/flexorch-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/flexorch-sdk)](https://pypi.org/project/flexorch-sdk/)
[![CI](https://github.com/flexorch/flexorch-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/flexorch/flexorch-sdk/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Python SDK for the [FlexOrch](https://flexorch.com) API.

FlexOrch turns unstructured documents (PDF, DOCX, invoices, emails…) into clean, structured, LLM-ready datasets — with automatic PII detection and masking, quality scoring, and multiple export formats.

---

## Install

```bash
pip install flexorch-sdk
```

Requires Python 3.10+. The only dependency is [`httpx`](https://www.python-httpx.org/).

---

## Quick start

```python
from flexorch_sdk import FlexOrchClient

client = FlexOrchClient("fx_your_key_here")

# Upload a document and wait for the pipeline to finish
job = client.process("contract.pdf", locale="tr").wait()

print(job.quality_grade)   # "A"
print(job.quality_score)   # 0.91

# Download the resulting dataset
dataset = job.dataset()
dataset.export("jsonl", path="output.jsonl")
```

---

## Auth

Pass your API key directly or set the `FLEXORCH_API_KEY` environment variable:

```bash
export FLEXORCH_API_KEY=fx_...
```

```python
from flexorch_sdk import FlexOrchClient

client = FlexOrchClient()   # reads FLEXORCH_API_KEY automatically
```

Get your API key from [app.flexorch.com](https://app.flexorch.com) → Settings.

---

## Supported input formats

| Category | Formats |
|---|---|
| Documents | PDF (text + scanned), DOCX, TXT |
| Spreadsheets | XLSX |
| Email | EML, MSG |
| E-invoices | XML/UBL (Peppol, GİB TR), FatturaPA (IT), XRechnung (DE), ZUGFeRD/Factur-X |
| Images | JPG, PNG, TIFF (OCR) |
| Web | HTML, HTM |

---

## Export formats

`json` · `jsonl` · `csv` · `parquet` · `md` · `xml` · `xlsx` · `rag`

```python
dataset.export("jsonl", path="output.jsonl")   # write to file
raw = dataset.export("parquet")                # return bytes
```

The `rag` format produces LlamaIndex/LangChain-compatible chunks with metadata.

---

## Processing

### Single file

```python
job = client.process("invoice.pdf", locale="de").wait()
```

`locale` is an [IETF language tag](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry)
used to activate the right PII detectors (`tr`, `de`, `en`, `fr`, `it`, `nl`, `es`, `pl`, `und` = all).

### Batch

```python
jobs = client.process_many(["a.pdf", "b.pdf", "c.pdf"], locale="und")
for job in jobs:
    job.wait()
    print(job.quality_grade, job.quality_score)
```

### From S3

```python
# Register a connector once; store conn.id for reuse
conn = client.connectors.create(
    "Production S3", "s3",
    {
        "bucket": "my-bucket",
        "region": "eu-central-1",
        "access_key_id": "AKIA...",
        "secret_access_key": "...",
    },
)

# Verify connectivity
result = client.connectors.test(conn.id)
print(result.success, result.latency_ms)   # True, 38

# Process files from S3
jobs = client.process_from_s3(conn.id, ["invoices/inv-001.pdf", "invoices/inv-002.pdf"])
for job in jobs:
    job.wait()
```

---

## Job polling

`Job.wait()` blocks until the pipeline completes or times out.

```python
job = client.process("large-report.pdf").wait(
    timeout=600,       # seconds before TimeoutError (default: 300)
    poll_interval=5,   # polling interval in seconds (default: 2)
)

print(job.status)        # "completed"
print(job.quality_grade) # "A" | "B" | "C" | "D"
print(job.quality_score) # 0.0 – 1.0
print(job.has_dataset)   # True
```

---

## Dataset operations

```python
ds = job.dataset()          # fetch dataset linked to this job
ds = client.datasets.get("dataset-id")

print(ds.name)              # "contract-2024-q1"
print(ds.row_count)         # 142
print(ds.available_formats) # ["json", "jsonl", "csv", "parquet"]

# Download locally
ds.export("jsonl", path="output.jsonl")

# Push directly to S3
push = ds.export_to_s3(conn.id, "jsonl", prefix="processed/datasets/")
print(push["s3_key"])       # "processed/datasets/contract-2024-q1.jsonl"
print(push["size_bytes"])   # 84320

# Semantic indexing (Pro+)
ds.index()
status = ds.index_status()  # {"status": "ready", "chunks_indexed": 48}
```

---

## Semantic search (Pro+)

```python
results = client.search(
    "payment terms net 30",
    top_k=10,
    filters={
        "document_type": "invoice",
        "language": "de",
        "quality_grade": "A",
        "pii_masked": True,
    },
)

for r in results:
    print(f"{r.score:.3f}  [{r.dataset_id}]  {r.text[:120]}")
```

---

## Resources

```python
# Jobs
jobs = client.jobs.list(page=1, page_size=20)
job  = client.jobs.get("job-id")

# Datasets
datasets = client.datasets.list()
ds       = client.datasets.get("dataset-id")

# Usage
usage = client.usage.current()
print(f"{usage.credits_used} / {usage.credits_limit} credits used")
print(f"Plan: {usage.plan}  —  resets {usage.reset_at}")

# Webhooks
client.webhooks.register("https://your-server.com/hook", events=["dataset.ready"])
client.webhooks.list()
client.webhooks.delete("webhook-id")

# Connectors
client.connectors.create("name", "s3", {...})
client.connectors.list()
client.connectors.get("connector-id")
client.connectors.test("connector-id")
client.connectors.delete("connector-id")
```

---

## Error handling

```python
from flexorch_sdk import (
    FlexOrchClient,
    AuthError,       # 401 — invalid or missing API key
    QuotaError,      # 402 — credit limit reached or trial expired
    RateLimitError,  # 429 — too many requests; has .retry_after (seconds)
    NotFoundError,   # 404
    ValidationError, # 422 — bad request parameters
    ServerError,     # 5xx
    JobFailedError,  # pipeline failed; has .job_id and .failure_reason
    TimeoutError,    # Job.wait() exceeded timeout; has .job_id
)

try:
    job = client.process("doc.pdf").wait(timeout=120)
except AuthError:
    print("Invalid API key — check FLEXORCH_API_KEY")
except QuotaError as e:
    print(f"Out of credits — reset at {e.reset_at}")
except JobFailedError as e:
    print(f"Pipeline failed for job {e.job_id}: {e.failure_reason}")
except TimeoutError as e:
    print(f"Job {e.job_id} still running after timeout — poll manually")
```

The SDK automatically retries `429` and `5xx` responses with exponential backoff (up to 3 attempts by default).

---

## Configuration

```python
client = FlexOrchClient(
    api_key="fx_...",
    base_url="https://api.flexorch.com/v1",  # override for self-hosted
    timeout=60.0,       # HTTP timeout per request in seconds
    max_retries=5,      # retry attempts for transient errors
)
```

### Context manager

```python
with FlexOrchClient() as client:
    job = client.process("report.pdf").wait()
    job.dataset().export("jsonl", path="report.jsonl")
# HTTP connection pool released automatically
```

---

## Examples

See [`examples/`](examples/) for runnable scripts:

| File | Description |
|---|---|
| [`basic_process.py`](examples/basic_process.py) | Process a single document and export as JSONL |
| [`batch_process.py`](examples/batch_process.py) | Process multiple files with error handling |
| [`s3_import.py`](examples/s3_import.py) | Import from S3, process, export results back to S3 |

---

## Development

```bash
git clone https://github.com/flexorch/flexorch-sdk
cd flexorch-sdk
pip install -e ".[dev]"
pytest
```

Tests use [respx](https://lundberg.github.io/respx/) to mock httpx — no network calls, no API key needed.

---

## Links

- [Platform](https://app.flexorch.com)
- [API reference](https://flexorch.com/developers)
- [flexorch-audit](https://github.com/flexorch/flexorch-audit) — open-source PII detection library

---

## License

[MIT](LICENSE)
