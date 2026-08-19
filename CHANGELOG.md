# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.3.1] — 2026-08-19

### Fixed

- **`job.build_dataset().wait().dataset()` — the exact chain this README documents — returned `None` even after the dataset was built successfully.** A completed `dataset_build` job reports its output via `dataset_summary.dataset_id`; neither top-level `has_dataset` nor `processing_summary` (which `Job.dataset()` relied on) is ever set for that job type, so the built dataset was unreachable from the job that built it. `Job._from_dict()` now reads `dataset_id` from `dataset_summary`, and `Job.dataset()` fetches `/datasets/{dataset_id}` directly when it's known. Found by exercising the documented one-liner against the live API — none of the mocked fixtures modeled a real `dataset_build` completion response.

---

## [0.3.0] — 2026-08-17

### Fixed (critical — the SDK did not work against the real API before this release)

- **`Transport` never unwrapped the `{status, data, error}` envelope every `/v1/*` endpoint returns** — every resource method received the raw envelope instead of its `data` payload, so parsed fields (`job.id`, `dataset.name`, ...) were silently wrong or empty. Fixed centrally in `Transport._request()`. The test suite's mocked fixtures previously modeled the *unwrapped* shape too, so this was never caught — all fixtures now mock the real wrapped responses.
- `FlexOrchClient.process()` sent the uploaded file under multipart field name `"file"` — the backend expects `"files"` (plural) and silently drops anything else, returning `400 MISSING_INPUT`. Fixed.
- `FlexOrchClient.process()` / `process_from_s3()` parsed the response as a single `Job` — the real `/data-process/async` response is `{accepted, rejected, jobs: [...]}` (the same multi-file-capable shape the UI uses). Now correctly unpacks `jobs[0]`, and raises `ValidationError` with the real rejection reason if the file was rejected instead of accepted.
- `Dataset.export()` called `GET /datasets/{id}/export?format=X` — the real route is `GET /datasets/{id}/export/{fmt}` (`fmt` is a path segment). Fixed; also added the `min_quality` param for `format="rag"`.
- `UsageResource.current()` called the non-existent `/usage/current` — the real endpoint is `GET /usage`, with a differently-shaped (nested `trial`/`usage.credits`) response. `UsageSnapshot` fields updated to match; `reset_at`/`period_start`/`period_end` (which the real API never returned) replaced with `is_trial`/`trial_ends_at`/`trial_days_remaining`.

### Added

- **`Job.build_dataset()`** / **`DatasetsResource.build_from_execution()`** — building a dataset from a completed job's execution is a separate, explicit API call (`POST /datasets/build-from-execution/{execution_id}`); it was previously undocumented and unreachable from the SDK, so `job.dataset()` on a fresh job always returned `None`. `Job.execution_id` is now parsed from `execution_summary`/`processing_summary`.
- `Dataset.rows()`, `Dataset.profile()`, `Dataset.compliance_report()` — row preview, quality/privacy profile, and KVKK/GDPR compliance report.
- `DocumentsResource` (`client.documents.get()` / `.list()`) and `Document.reprocess()`.
- `ConnectorsResource` scheduled-sync methods: `create_schedule()`, `list_schedules()`, `delete_schedule()`, `trigger_schedule()`, `schedule_logs()`.
- `JobsResource.submit_feedback()` / `.get_feedback()`.
- `UsageResource.history()`, `.quality_trend()`, `.rate_limits()`.

### Changed

- README quick start and all `examples/*.py` updated to include the now-required `job.build_dataset().wait()` step before `.dataset()`.

---

## [0.2.3] — 2026-08-06

### Added

- `Job.degraded` — `True` when the underlying pipeline execution completed but one or more non-critical steps failed (e.g. structured extraction couldn't find a table in the document). The job still succeeds — PII detection and quality scoring results are still meaningful — but `records`/columns may be empty. Read from the API's `execution_summary.degraded` field; defaults to `False` for jobs with no execution (e.g. `dataset_build`). `Job.wait()` does not raise for a degraded completion.

---

## [0.2.2] — 2026-07-21

### Added

- `ConnectorsResource.create()` — `pgvector_external`, `pinecone`, `qdrant` added to the accepted connector `type` values (vector destinations for dataset indexing `push_only`/`both` modes)

---

## [0.2.1] — 2026-07-21

### Added

- `ConnectorsResource.create()` — `google_drive` added to the accepted connector `type` values (service-account based; requires `folder_id` + `credentials_json` in `config`)

---

## [0.2.0] — 2026-07-05

### Added

**RAG submodule (`flexorch_sdk.rag`)**
- `RAGDocument` — text chunk with `page_content` + `metadata`; duck-type compatible with both LangChain `Document` and LlamaIndex `Document` (via `.text` property alias)
- `FlexOrchRetriever` — LangChain-compatible retriever backed by `/v1/search`; supports `quality_threshold`, `pii_masked`, `top_k`, `mode`, `document_type`, `language` filters; implements `get_relevant_documents` and `aget_relevant_documents` shims for older LangChain versions
- `FlexOrchReader` — LlamaIndex-compatible reader backed by `/v1/datasets/{id}/chunks`; auto-paginates, supports `min_quality` and `pii_masked_only` filters

**Dataset model**
- `Dataset.chunks(page, page_size, quality_grade, pii_masked)` — paginated RAG chunk retrieval (Pro+ plan required)
- `hf` added to supported export formats (`Dataset.export("hf")`)

**Search**
- `client.search(query, mode=..., ...)` — new `mode` parameter (auto / hybrid / semantic / structured); passes to `/v1/search` query

**Tests**
- `tests/test_rag_helpers.py` — FlexOrchRetriever + FlexOrchReader unit tests

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
