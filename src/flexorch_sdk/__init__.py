"""
flexorch-sdk — Python SDK for the FlexOrch API.

    from flexorch_sdk import FlexOrchClient

    client = FlexOrchClient("fx_your_key_here")

    # Process a document and wait for the result
    job = client.process("contract.pdf", locale="tr").wait()
    print(job.quality_grade)   # "A"

    # Build a dataset from the job, then download it as JSONL
    dataset = job.build_dataset().wait().dataset()
    dataset.export("jsonl", path="output.jsonl")

    # Or use the context manager
    with FlexOrchClient("fx_...") as client:
        jobs = client.process_many(["a.pdf", "b.pdf"])
        for job in jobs:
            job.wait()
"""

from .client import FlexOrchClient
from .errors import (
    AuthError,
    FlexOrchError,
    JobFailedError,
    NotFoundError,
    QuotaError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .models.connector import Connector, ConnectorTestResult, SyncLog, SyncSchedule
from .models.dataset import Dataset
from .models.document import Document
from .models.job import Job, JobFeedback
from .models.search import SearchResult
from .rag import FlexOrchReader, FlexOrchRetriever, RAGDocument
from .resources.usage import (
    QualityTrendItem,
    RateLimitStatus,
    UsageHistoryItem,
    UsageSnapshot,
)
from .resources.webhooks import Webhook

__version__ = "0.3.1"

__all__ = [
    "AuthError",
    "Connector",
    "ConnectorTestResult",
    "Dataset",
    "Document",
    "FlexOrchClient",
    "FlexOrchError",
    "FlexOrchReader",
    "FlexOrchRetriever",
    "Job",
    "JobFailedError",
    "JobFeedback",
    "NotFoundError",
    "QualityTrendItem",
    "QuotaError",
    "RAGDocument",
    "RateLimitError",
    "RateLimitStatus",
    "SearchResult",
    "ServerError",
    "SyncLog",
    "SyncSchedule",
    "TimeoutError",
    "UsageHistoryItem",
    "UsageSnapshot",
    "ValidationError",
    "Webhook",
    "__version__",
]
