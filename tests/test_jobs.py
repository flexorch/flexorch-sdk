"""Tests for Job model — wait(), dataset(), build_dataset(), polling logic."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient, JobFailedError
from flexorch_sdk.errors import TimeoutError
from conftest import envelope, accepted

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
        httpx.Response(200, json=envelope({"job_id": "j1", "status": "running"})),
        httpx.Response(200, json=envelope({"job_id": "j1", "status": "running"})),
        httpx.Response(200, json=envelope({"job_id": "j1", "status": "completed", "has_dataset": True})),
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
        return_value=httpx.Response(200, json=envelope({
            "job_id": "j1",
            "status": "failed",
            "failure_reason": "EMPTY_DOCUMENT",
        }))
    )

    job = Job(id="j1", status="queued", _transport=transport)
    with pytest.raises(JobFailedError) as exc_info:
        job.wait(poll_interval=0)
    assert "EMPTY_DOCUMENT" in str(exc_info.value)


@respx.mock
def test_wait_raises_on_timeout(transport):
    from flexorch_sdk.models.job import Job

    respx.get(f"{BASE}/jobs/j1").mock(
        return_value=httpx.Response(200, json=envelope({"job_id": "j1", "status": "running"}))
    )

    job = Job(id="j1", status="queued", _transport=transport)
    with pytest.raises(TimeoutError):
        job.wait(timeout=1, poll_interval=0)


@respx.mock
def test_wait_surfaces_degraded_from_execution_summary(transport):
    from flexorch_sdk.models.job import Job

    respx.get(f"{BASE}/jobs/j1").mock(
        return_value=httpx.Response(200, json=envelope({
            "job_id": "j1",
            "status": "completed",
            "execution_summary": {"execution_id": 1, "status": "completed", "degraded": True},
        }))
    )

    job = Job(id="j1", status="queued", _transport=transport)
    result = job.wait(poll_interval=0)
    assert result.degraded is True


def test_degraded_defaults_to_false_without_execution_summary():
    from flexorch_sdk.models.job import Job

    job = Job._from_dict({"job_id": "j1", "status": "completed"}, transport=None)
    assert job.degraded is False


def test_degraded_false_when_execution_summary_says_false():
    from flexorch_sdk.models.job import Job

    job = Job._from_dict(
        {"job_id": "j1", "status": "completed", "execution_summary": {"degraded": False}},
        transport=None,
    )
    assert job.degraded is False


def test_execution_id_read_from_execution_summary():
    from flexorch_sdk.models.job import Job

    job = Job._from_dict(
        {"job_id": "j1", "status": "completed", "execution_summary": {"execution_id": 42, "degraded": False}},
        transport=None,
    )
    assert job.execution_id == 42


@respx.mock
def test_dataset_returns_none_when_no_dataset(transport):
    from flexorch_sdk.models.job import Job
    job = Job(id="j1", status="completed", has_dataset=False, _transport=transport)
    assert job.dataset() is None


@respx.mock
def test_dataset_fetches_when_has_dataset(transport):
    from flexorch_sdk.models.job import Job

    respx.get(f"{BASE}/datasets").mock(
        return_value=httpx.Response(200, json=envelope({"items": [{
            "id": "ds-1", "name": "My Dataset", "slug": "my-dataset",
            "status": "ready", "row_count": 10,
        }]}))
    )

    job = Job(id="j1", status="completed", has_dataset=True, _transport=transport)
    ds = job.dataset()
    assert ds is not None
    assert ds.id == "ds-1"
    assert ds.row_count == 10


# ── build_dataset() ────────────────────────────────────────────────────────────

@respx.mock
def test_build_dataset_posts_to_build_from_execution(transport):
    from flexorch_sdk.models.job import Job

    route = respx.post(f"{BASE}/datasets/build-from-execution/42").mock(
        return_value=httpx.Response(202, json=accepted({
            "job_id": "job-build-1", "job_type": "dataset_build", "status": "queued", "reference_id": 42,
        }))
    )

    job = Job(id="j1", status="completed", execution_id=42, _transport=transport)
    build_job = job.build_dataset(name="my-dataset")
    assert build_job.id == "job-build-1"
    assert route.called

    import json
    body = json.loads(route.calls[0].request.content)
    assert body["name"] == "my-dataset"


def test_build_dataset_without_execution_id_raises(transport):
    from flexorch_sdk.models.job import Job

    job = Job(id="j1", status="completed", execution_id=None, _transport=transport)
    with pytest.raises(ValueError, match="execution_id"):
        job.build_dataset()
