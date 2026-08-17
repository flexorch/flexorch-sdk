"""Tests for DatasetsResource, DocumentsResource, UsageResource, WebhooksResource, job feedback."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient
from flexorch_sdk.resources.webhooks import WebhooksResource
from conftest import envelope, accepted

BASE = "https://api.flexorch.com/v1"


@pytest.fixture
def client():
    return FlexOrchClient("fx_test", base_url=BASE)


# ── Datasets ──────────────────────────────────────────────────────────────────

@respx.mock
def test_datasets_list(client):
    respx.get(f"{BASE}/datasets").mock(return_value=httpx.Response(200, json=envelope({
        "items": [
            {"id": "d1", "name": "A", "slug": "a", "status": "ready", "row_count": 5},
            {"id": "d2", "name": "B", "slug": "b", "status": "ready", "row_count": 0},
        ]
    })))
    datasets = client.datasets.list()
    assert len(datasets) == 2
    assert datasets[0].id == "d1"


@respx.mock
def test_datasets_get(client):
    respx.get(f"{BASE}/datasets/d1").mock(return_value=httpx.Response(200, json=envelope({
        "id": "d1", "name": "My Dataset", "slug": "my-ds", "status": "ready", "row_count": 42,
    })))
    ds = client.datasets.get("d1")
    assert ds.name == "My Dataset"
    assert ds.row_count == 42


@respx.mock
def test_dataset_export(client):
    respx.get(f"{BASE}/datasets").mock(return_value=httpx.Response(200, json=envelope({
        "items": [{"id": "d1", "name": "A", "slug": "a", "status": "ready", "row_count": 1}]
    })))
    # fmt is a *path segment*, not a query param — GET /datasets/{id}/export/{fmt}.
    respx.get(f"{BASE}/datasets/d1/export/jsonl").mock(
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


@respx.mock
def test_dataset_export_rag_with_min_quality(client):
    route = respx.get(f"{BASE}/datasets/d1/export/rag").mock(
        return_value=httpx.Response(200, content=b'[]')
    )
    from flexorch_sdk.models.dataset import Dataset
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    ds.export("rag", min_quality="B")
    assert route.called
    assert route.calls[0].request.url.params["min_quality"] == "B"


@respx.mock
def test_dataset_build_from_execution(client):
    route = respx.post(f"{BASE}/datasets/build-from-execution/7").mock(
        return_value=httpx.Response(202, json=accepted({
            "job_id": "job-9", "job_type": "dataset_build", "status": "queued", "reference_id": 7,
        }))
    )
    job = client.datasets.build_from_execution(7, force_rebuild=True)
    assert job.id == "job-9"
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["force_rebuild"] is True


@respx.mock
def test_dataset_rows(client):
    respx.get(f"{BASE}/datasets/d1/rows").mock(return_value=httpx.Response(200, json=envelope({
        "dataset_id": 1, "columns": ["vendor", "total"], "rows": [{"vendor": "Acme", "total": 100}],
        "pagination": {"page": 1, "page_size": 50, "total_rows": 1, "filtered_total": 1, "returned_rows": 1, "has_next": False},
    })))
    from flexorch_sdk.models.dataset import Dataset
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    result = ds.rows()
    assert result["rows"][0]["vendor"] == "Acme"


@respx.mock
def test_dataset_profile(client):
    respx.get(f"{BASE}/datasets/d1/profile").mock(return_value=httpx.Response(200, json=envelope({
        "quality": {"grade_distribution": {"A": 1}, "avg_score": 0.9, "below_threshold_count": 0},
        "privacy": {"pii_findings_count": 2, "masked_record_count": 1, "clean_record_count": 0},
        "formats": ["jsonl"], "columns": ["vendor"],
    })))
    from flexorch_sdk.models.dataset import Dataset
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    profile = ds.profile()
    assert profile["privacy"]["pii_findings_count"] == 2


@respx.mock
def test_dataset_compliance_report(client):
    respx.get(f"{BASE}/datasets/d1/compliance-report").mock(return_value=httpx.Response(200, json=envelope({
        "dataset_id": 1, "dataset_name": "x", "pii_findings_count": 3,
        "kvkk_categories": ["kimlik verisi"], "gdpr_categories": [],
        "applicable_regulations": [], "plan_coverage": "pro_countries",
    })))
    from flexorch_sdk.models.dataset import Dataset
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    report = ds.compliance_report()
    assert report["pii_findings_count"] == 3


# ── Documents ─────────────────────────────────────────────────────────────────

@respx.mock
def test_documents_list(client):
    respx.get(f"{BASE}/documents").mock(return_value=httpx.Response(200, json=envelope({
        "items": [{"id": 1, "filename": "a.pdf", "file_ext": ".pdf", "status": "processed", "storage_path": "s3://x"}],
        "total": 1, "page": 1, "page_size": 20,
    })))
    docs = client.documents.list()
    assert len(docs) == 1
    assert docs[0].filename == "a.pdf"


@respx.mock
def test_documents_get(client):
    respx.get(f"{BASE}/documents/1").mock(return_value=httpx.Response(200, json=envelope({
        "id": 1, "filename": "a.pdf", "file_ext": ".pdf", "status": "processed", "storage_path": "s3://x",
        "processing_history": [{"job_id": 5, "status": "completed", "executed_at": "2026-01-01", "quality_grade": "A"}],
        "related_datasets": [],
    })))
    doc = client.documents.get("1")
    assert doc.processing_history[0]["quality_grade"] == "A"


@respx.mock
def test_document_reprocess(client):
    from flexorch_sdk.models.document import Document
    respx.post(f"{BASE}/documents/1/reprocess").mock(return_value=httpx.Response(202, json=accepted({
        "job_id": 42, "job_type": "data_process", "status": "queued", "document_id": 1,
    })))
    doc = Document(id="1", filename="a.pdf", file_ext=".pdf", status="processed", storage_path="s3://x", _transport=client._transport)
    job = doc.reprocess()
    assert job.id == "42"


# ── Usage ─────────────────────────────────────────────────────────────────────

@respx.mock
def test_usage_current(client):
    respx.get(f"{BASE}/usage").mock(return_value=httpx.Response(200, json=envelope({
        "plan": "starter",
        "trial": None,
        "usage": {"credits": {"used": 120, "limit": 1200, "remaining": 1080}},
    })))
    usage = client.usage.current()
    assert usage.plan == "starter"
    assert usage.credits_remaining == 1080
    assert usage.is_trial is False


@respx.mock
def test_usage_current_trial_plan(client):
    respx.get(f"{BASE}/usage").mock(return_value=httpx.Response(200, json=envelope({
        "plan": "trial",
        "trial": {"is_trial": True, "trial_ends_at": "2026-09-01", "trial_days_remaining": 5},
        "usage": {"credits": {"used": 10, "limit": 1200, "remaining": 1190}},
    })))
    usage = client.usage.current()
    assert usage.is_trial is True
    assert usage.trial_days_remaining == 5


@respx.mock
def test_usage_history(client):
    respx.get(f"{BASE}/usage/history").mock(return_value=httpx.Response(200, json=envelope([
        {"date": "2026-08-01", "credits_used": 10, "jobs_count": 2},
        {"date": "2026-08-02", "credits_used": 5, "jobs_count": 1},
    ])))
    history = client.usage.history(period="7d")
    assert len(history) == 2
    assert history[0].credits_used == 10


@respx.mock
def test_usage_quality_trend(client):
    respx.get(f"{BASE}/usage/quality-trend").mock(return_value=httpx.Response(200, json=envelope([
        {"date": "2026-08-01", "avg_quality_score": 0.9, "grade_distribution": {"A": 3}, "avg_field_fill_rate": 0.8, "job_count": 3},
    ])))
    trend = client.usage.quality_trend()
    assert trend[0].avg_quality_score == 0.9


@respx.mock
def test_usage_rate_limits(client):
    respx.get(f"{BASE}/usage/rate-limits").mock(return_value=httpx.Response(200, json=envelope({
        "plan": "starter", "unlimited": False, "limit": 100, "used": 10,
        "remaining": 90, "window_seconds": 60, "reset_in_seconds": 30,
    })))
    status = client.usage.rate_limits()
    assert status.remaining == 90


# ── Webhooks ──────────────────────────────────────────────────────────────────

@respx.mock
def test_webhooks_register(client):
    respx.post(f"{BASE}/webhooks").mock(return_value=httpx.Response(201, json=envelope({
        "id": "wh-1", "url": "https://example.com/hook",
        "events": ["dataset.ready"], "active": True, "created_at": "2026-05-24",
    })))
    wh = client.webhooks.register("https://example.com/hook", events=["dataset.ready"])
    assert wh.id == "wh-1"
    assert "dataset.ready" in wh.events


def test_webhooks_register_invalid_event(client):
    with pytest.raises(ValueError, match="Unknown event"):
        client.webhooks.register("https://example.com/hook", events=["invalid.event"])


@respx.mock
def test_webhooks_list(client):
    respx.get(f"{BASE}/webhooks").mock(return_value=httpx.Response(200, json=envelope({
        "items": [{"id": "wh-1", "url": "https://x.com", "events": [], "active": True, "created_at": ""}]
    })))
    hooks = client.webhooks.list()
    assert len(hooks) == 1


@respx.mock
def test_webhooks_delete(client):
    respx.delete(f"{BASE}/webhooks/wh-1").mock(return_value=httpx.Response(204))
    client.webhooks.delete("wh-1")


# ── Jobs resource ──────────────────────────────────────────────────────────────

@respx.mock
def test_jobs_get(client):
    respx.get(f"{BASE}/jobs/j1").mock(return_value=httpx.Response(200, json=envelope({
        "job_id": "j1", "status": "completed",
        "quality": {"grade": "A", "score": 0.92},
    })))
    job = client.jobs.get("j1")
    assert job.quality_grade == "A"


@respx.mock
def test_jobs_list(client):
    respx.get(f"{BASE}/jobs").mock(return_value=httpx.Response(200, json=envelope({
        "items": [
            {"job_id": "j1", "status": "completed"},
            {"job_id": "j2", "status": "running"},
        ]
    })))
    jobs = client.jobs.list()
    assert len(jobs) == 2


@respx.mock
def test_jobs_submit_feedback(client):
    respx.post(f"{BASE}/jobs/j1/feedback").mock(return_value=httpx.Response(200, json=envelope({
        "id": 1, "job_id": "j1", "rating": "up", "issue": None, "notes": "great", "created_at": "2026-08-17",
    })))
    fb = client.jobs.submit_feedback("j1", "up", notes="great")
    assert fb.rating == "up"


def test_jobs_submit_feedback_invalid_rating(client):
    with pytest.raises(ValueError, match="Invalid rating"):
        client.jobs.submit_feedback("j1", "sideways")


def test_jobs_submit_feedback_invalid_issue(client):
    with pytest.raises(ValueError, match="Invalid issue"):
        client.jobs.submit_feedback("j1", "down", issue="not_a_real_issue")


@respx.mock
def test_jobs_get_feedback_none(client):
    respx.get(f"{BASE}/jobs/j1/feedback").mock(return_value=httpx.Response(200, json=envelope(None)))
    assert client.jobs.get_feedback("j1") is None


@respx.mock
def test_jobs_get_feedback_existing(client):
    respx.get(f"{BASE}/jobs/j1/feedback").mock(return_value=httpx.Response(200, json=envelope({
        "id": 1, "job_id": "j1", "rating": "down", "issue": "missing_fields", "notes": None, "created_at": "2026-08-17",
    })))
    fb = client.jobs.get_feedback("j1")
    assert fb.issue == "missing_fields"
