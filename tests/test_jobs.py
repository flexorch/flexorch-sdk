"""Tests for Job model — wait(), dataset(), polling logic."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient, JobFailedError
from flexorch_sdk.errors import TimeoutError

BASE = "https://api.flexorch.com/v1"


@pytest.fixture
def transport():
    return FlexOrchClient("fx_test", base_url=BASE)._transport


@respx.mock
def test_wait_already_completed(transport):
    from flexorch_sdk.models.job import Job
    job = Job(id="j1", status="completed", _transport=transport)
    result = job.wait()
    assert result.status == "completed"


@respx.mock
def test_wait_polls_until_completed(transport):
    from flexorch_sdk.models.job import Job

    responses = [
        httpx.Response(200, json={"job_id": "j1", "status": "running"}),
        httpx.Response(200, json={"job_id": "j1", "status": "running"}),
        httpx.Response(200, json={"job_id": "j1", "status": "completed", "has_dataset": True}),
    ]
    respx.get(f"{BASE}/jobs/j1").mock(side_effect=responses)

    job = Job(id="j1", status="queued", _transport=transport)
    result = job.wait(poll_interval=0)
    assert result.status == "completed"
    assert result.has_dataset is True


@respx.mock
def test_wait_raises_on_failed(transport):
    from flexorch_sdk.models.job import Job

    respx.get(f"{BASE}/jobs/j1").mock(
        return_value=httpx.Response(200, json={
            "job_id": "j1",
            "status": "failed",
            "failure_reason": "EMPTY_DOCUMENT",
        })
    )

    job = Job(id="j1", status="queued", _transport=transport)
    with pytest.raises(JobFailedError) as exc_info:
        job.wait(poll_interval=0)
    assert "EMPTY_DOCUMENT" in str(exc_info.value)


@respx.mock
def test_wait_raises_on_timeout(transport):
    from flexorch_sdk.models.job import Job

    respx.get(f"{BASE}/jobs/j1").mock(
        return_value=httpx.Response(200, json={"job_id": "j1", "status": "running"})
    )

    job = Job(id="j1", status="queued", _transport=transport)
    with pytest.raises(TimeoutError):
        job.wait(timeout=1, poll_interval=0)


@respx.mock
def test_dataset_returns_none_when_no_dataset(transport):
    from flexorch_sdk.models.job import Job
    job = Job(id="j1", status="completed", has_dataset=False, _transport=transport)
    assert job.dataset() is None


@respx.mock
def test_dataset_fetches_when_has_dataset(transport):
    from flexorch_sdk.models.job import Job

    respx.get(f"{BASE}/datasets").mock(
        return_value=httpx.Response(200, json={"items": [{
            "id": "ds-1", "name": "My Dataset", "slug": "my-dataset",
            "status": "ready", "row_count": 10,
        }]})
    )

    job = Job(id="j1", status="completed", has_dataset=True, _transport=transport)
    ds = job.dataset()
    assert ds is not None
    assert ds.id == "ds-1"
    assert ds.row_count == 10
