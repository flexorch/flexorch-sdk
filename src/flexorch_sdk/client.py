from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ._transport import Transport
from .errors import ValidationError
from .models.job import Job
from .models.search import SearchResult
from .resources.connectors import ConnectorsResource
from .resources.datasets import DatasetsResource
from .resources.documents import DocumentsResource
from .resources.jobs import JobsResource
from .resources.usage import UsageResource
from .resources.webhooks import WebhooksResource

_DEFAULT_BASE_URL = "https://api.flexorch.com/v1"


def _first_job_or_raise(upload_response: dict[str, Any], filename: str, transport: Transport) -> Job:
    """Unpack a single-file /data-process/async response into its Job.

    The endpoint always returns {accepted, rejected, jobs: [...]} even for a
    single file (it's the same multi-file-capable response the UI uses).
    """
    jobs = upload_response.get("jobs") or []
    if jobs:
        return Job._from_dict(jobs[0], transport)
    rejected = upload_response.get("rejected") or []
    reason = rejected[0].get("error") if rejected else "unknown error"
    raise ValidationError(f"{filename} was rejected: {reason}")


class FlexOrchClient:
    """Main entry point for the FlexOrch API.

    Args:
        api_key:     Your FlexOrch API key (fx_...).
                     Defaults to FLEXORCH_API_KEY environment variable.
        base_url:    Override the API base URL (useful for testing).
        timeout:     HTTP timeout in seconds. Default: 30.
        max_retries: Maximum retry attempts for transient errors. Default: 3.

    Example::

        from flexorch_sdk import FlexOrchClient

        client = FlexOrchClient("fx_your_key_here")
        job = client.process("contract.pdf", locale="tr").wait()
        dataset = job.build_dataset().wait().dataset()
        dataset.export("jsonl", path="output.jsonl")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        resolved_key = api_key or os.environ.get("FLEXORCH_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "No API key provided. Pass api_key= or set the FLEXORCH_API_KEY environment variable."
            )

        self._transport = Transport(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        self.jobs = JobsResource(self._transport)
        self.datasets = DatasetsResource(self._transport)
        self.documents = DocumentsResource(self._transport)
        self.usage = UsageResource(self._transport)
        self.webhooks = WebhooksResource(self._transport)
        self.connectors = ConnectorsResource(self._transport)

    def process(
        self,
        file_path: str | Path,
        *,
        locale: str = "und",
        pipeline_config: dict[str, Any] | None = None,
    ) -> Job:
        """Upload a document and start the processing pipeline.

        Args:
            file_path:       Path to the file (PDF, DOCX, TXT, XLSX, …).
            locale:          Language hint for PII detection.
                             "und" = all detectors (default), "tr", "de", "en", etc.
            pipeline_config: Optional pipeline overrides passed to the API.

        Returns:
            A :class:`Job` object. Call ``.wait()`` to block until processing completes.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        form: dict[str, Any] = {"locale": locale}
        if pipeline_config:
            import json
            form["pipeline_config"] = json.dumps(pipeline_config)

        with path.open("rb") as fh:
            data = self._transport.post(
                "/data-process/async",
                # Backend param is `files: list[UploadFile]` — the multipart
                # field name must be "files" (plural), not "file", or FastAPI
                # never binds it and the request 400s with MISSING_INPUT.
                files={"files": (path.name, fh, "application/octet-stream")},
                data=form,
            )

        return _first_job_or_raise(data, path.name, self._transport)

    def process_many(
        self,
        file_paths: list[str | Path],
        *,
        locale: str = "und",
    ) -> list[Job]:
        """Upload and start processing for multiple files sequentially.

        Returns:
            List of :class:`Job` objects in the same order as *file_paths*.
        """
        return [self.process(p, locale=locale) for p in file_paths]

    def process_from_s3(
        self,
        connector_id: str,
        keys: list[str],
        *,
        locale: str = "und",
        pipeline_config: dict[str, Any] | None = None,
    ) -> list[Job]:
        """Start processing for files already stored in an S3 connector.

        Args:
            connector_id: ID of an active S3 connector.
            keys:         List of S3 object keys to process.
            locale:       Language hint for PII detection.
            pipeline_config: Optional pipeline overrides.

        Returns:
            List of :class:`Job` objects, one per key.
        """
        import json as _json

        jobs = []
        for key in keys:
            source = {"connector_id": connector_id, "keys": [key]}
            form: dict[str, Any] = {
                "locale": locale,
                "source": _json.dumps(source),
            }
            if pipeline_config:
                form["pipeline_config"] = _json.dumps(pipeline_config)
            data = self._transport.post("/data-process/async", data=form)
            jobs.append(_first_job_or_raise(data, key, self._transport))
        return jobs

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        mode: str = "auto",
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Semantic search across all indexed datasets (Pro+ plan required).

        Args:
            query:   Natural language search query.
            top_k:   Number of results to return (1–50). Default: 10.
            mode:    Search mode: ``"auto"`` | ``"semantic"`` | ``"hybrid"`` | ``"structured"``.
                     Default: ``"auto"`` (routes by document type and plan).
            filters: Optional filter dict. Supported keys:
                     ``document_type``, ``language``, ``pii_masked``, ``quality_grade``.

        Returns:
            List of :class:`SearchResult` sorted by descending cosine score.
        """
        body: dict[str, Any] = {"query": query, "top_k": top_k, "mode": mode}
        if filters:
            body["filters"] = filters
        data = self._transport.post("/search", json=body) or {}
        items = data.get("results", [])
        return [SearchResult._from_dict(item) for item in items]

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._transport.close()

    def __enter__(self) -> FlexOrchClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"FlexOrchClient(base_url={self._transport._base_url!r})"
