# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-05-24

Initial release.

### Added

**Core**
- `FlexOrchClient` — main entry point; reads `FLEXORCH_API_KEY` env var automatically
- `Transport` — httpx-based HTTP layer with automatic retry (3×, exponential backoff) on `429` and `5xx`
- Context manager support (`with FlexOrchClient() as client: ...`)

**Processing**
- `client.process(file_path, locale, pipeline_config)` — upload a document and start the pipeline
- `client.process_many(file_paths, locale)` — sequential batch processing
- `client.process_from_s3(connector_id, keys, locale)` — import directly from an S3 connector

**Jobs**
- `Job.wait(timeout, poll_interval)` — blocking poll until `completed` or `failed`
- `Job.dataset()` — fetch the linked dataset once the job is done
- `client.jobs.get(job_id)` / `client.jobs.list(page, page_size)`

**Datasets**
- `Dataset.export(format, path)` — download in `json`, `jsonl`, `csv`, `parquet`, `md`, `xml`, `xlsx`, or `rag`
- `Dataset.export_to_s3(connector_id, format, prefix)` — push directly to S3
- `Dataset.index()` / `Dataset.index_status()` — semantic indexing (Pro+)
- `client.datasets.get(dataset_id)` / `client.datasets.list()`

**Semantic search**
- `client.search(query, top_k, filters)` — cosine similarity search across indexed datasets (Pro+)

**Connectors**
- `client.connectors.create(name, type, config)` — register an S3 connector
- `client.connectors.list()` / `get(id)` / `delete(id)` / `test(id)`

**Usage & Webhooks**
- `client.usage.current()` — credits used/remaining, plan, reset date
- `client.webhooks.register(url, events)` / `list()` / `delete(id)`

**Errors**
- `FlexOrchError`, `AuthError`, `QuotaError`, `RateLimitError`, `NotFoundError`,
  `ValidationError`, `ServerError`, `JobFailedError`, `TimeoutError`
