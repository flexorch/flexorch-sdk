"""
flexorch-sdk — Python SDK for the FlexOrch API.

    from flexorch_sdk import FlexOrchClient

    client = FlexOrchClient("fx_your_key_here")

    # Process a document and wait for the result
    job = client.process("contract.pdf", locale="tr").wait()
    print(job.quality_grade)   # "A"

    # Download the dataset as JSONL
    dataset = job.dataset()
    dataset.export("jsonl", path="output.jsonl")

    # Or use the context manager
    with FlexOrchClient("fx_...") as client:
        jobs = client.process_many(["a.pdf", "b.pdf"])
        for job in jobs:
            job.wait()
"""

from .client import FlexOrchClient
from .models.job import Job
from .models.dataset import Dataset
from .models.connector import Connector, ConnectorTestResult
from .models.search import SearchResult
from .resources.usage import UsageSnapshot
from .resources.webhooks import Webhook
from .errors import (
    FlexOrchError,
    AuthError,
    QuotaError,
    RateLimitError,
    NotFoundError,
    ValidationError,
    ServerError,
    JobFailedError,
    TimeoutError,
)

__version__ = "0.1.0"

__all__ = [
    "FlexOrchClient",
    "Job",
    "Dataset",
    "Connector",
    "ConnectorTestResult",
    "SearchResult",
    "UsageSnapshot",
    "Webhook",
    "FlexOrchError",
    "AuthError",
    "QuotaError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
    "ServerError",
    "JobFailedError",
    "TimeoutError",
    "__version__",
]
