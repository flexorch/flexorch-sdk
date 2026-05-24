"""Tests for DatasetsResource, UsageResource, WebhooksResource."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient
from flexorch_sdk.resources.webhooks import WebhooksResource

BASE = "https://api.flexorch.com/v1"


@pytest.fixture
def client():
    return FlexOrchClient("fx_test", base_url=BASE)


# ── Datasets ──────────────────────────────────────────────────────────────────

@respx.mock
def test_datasets_list(client):
    respx.get(f"{BASE}/datasets").mock(return_value=httpx.Response(200, json={
        "items": [
            {"id": "d1", "name": "A", "slug": "a", "status": "ready", "row_count": 5},
            {"id": "d2", "name": "B", "slug": "b", "status": "ready", "row_count": 0},
        ]
    }))
    datasets = client.datasets.list()
    assert len(datasets) == 2
    assert datasets[0].id == "d1"


@respx.mock
def test_datasets_get(client):
    respx.get(f"{BASE}/datasets/d1").mock(return_value=httpx.Response(200, json={
        "id": "d1", "name": "My Dataset", "slug": "my-ds", "status": "ready", "row_count": 42,
    }))
    ds = client.datasets.get("d1")
    assert ds.name == "My Dataset"
    assert ds.row_count == 42


@respx.mock
def test_dataset_export(client):
    respx.get(f"{BASE}/datasets").mock(return_value=httpx.Response(200, json={
        "items": [{"id": "d1", "name": "A", "slug": "a", "status": "ready", "row_count": 1}]
    }))
    respx.get(f"{BASE}/datasets/d1/export").mock(
        return_value=httpx.Response(200, content=b'{"row":1}\n')
    )
    ds = client.datasets.list()[0]
    raw = ds.export("jsonl")
    assert raw == b'{"row":1}\n'


def test_dataset_export_invalid_format(client):
    from flexorch_sdk.models.dataset import Dataset
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    with pytest.raises(ValueError, match="Unsupported format"):
        ds.export("pdf")


# ── Usage ─────────────────────────────────────────────────────────────────────

@respx.mock
def test_usage_current(client):
    respx.get(f"{BASE}/usage/current").mock(return_value=httpx.Response(200, json={
        "plan": "starter",
        "credits_used": 120,
        "credits_limit": 1200,
        "credits_remaining": 1080,
        "reset_at": "2026-06-01",
        "period_start": "2026-05-01",
        "period_end": "2026-05-31",
    }))
    usage = client.usage.current()
    assert usage.plan == "starter"
    assert usage.credits_remaining == 1080


# ── Webhooks ──────────────────────────────────────────────────────────────────

@respx.mock
def test_webhooks_register(client):
    respx.post(f"{BASE}/webhooks").mock(return_value=httpx.Response(201, json={
        "id": "wh-1", "url": "https://example.com/hook",
        "events": ["dataset.ready"], "active": True, "created_at": "2026-05-24",
    }))
    wh = client.webhooks.register("https://example.com/hook", events=["dataset.ready"])
    assert wh.id == "wh-1"
    assert "dataset.ready" in wh.events


def test_webhooks_register_invalid_event(client):
    with pytest.raises(ValueError, match="Unknown event"):
        client.webhooks.register("https://example.com/hook", events=["invalid.event"])


@respx.mock
def test_webhooks_list(client):
    respx.get(f"{BASE}/webhooks").mock(return_value=httpx.Response(200, json={
        "items": [{"id": "wh-1", "url": "https://x.com", "events": [], "active": True, "created_at": ""}]
    }))
    hooks = client.webhooks.list()
    assert len(hooks) == 1


@respx.mock
def test_webhooks_delete(client):
    respx.delete(f"{BASE}/webhooks/wh-1").mock(return_value=httpx.Response(204))
    client.webhooks.delete("wh-1")


# ── Jobs resource ──────────────────────────────────────────────────────────────

@respx.mock
def test_jobs_get(client):
    respx.get(f"{BASE}/jobs/j1").mock(return_value=httpx.Response(200, json={
        "job_id": "j1", "status": "completed",
        "quality": {"grade": "A", "score": 0.92},
    }))
    job = client.jobs.get("j1")
    assert job.quality_grade == "A"


@respx.mock
def test_jobs_list(client):
    respx.get(f"{BASE}/jobs").mock(return_value=httpx.Response(200, json={
        "items": [
            {"job_id": "j1", "status": "completed"},
            {"job_id": "j2", "status": "running"},
        ]
    }))
    jobs = client.jobs.list()
    assert len(jobs) == 2
