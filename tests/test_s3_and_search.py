"""Tests for ConnectorsResource, connector schedules, process_from_s3, dataset.export_to_s3, client.search."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient, Connector, ConnectorTestResult, SearchResult
from flexorch_sdk.models.dataset import Dataset
from conftest import envelope, accepted

BASE = "https://api.flexorch.com/v1"


@pytest.fixture
def client():
    return FlexOrchClient("fx_test", base_url=BASE)


# ── ConnectorsResource ─────────────────────────────────────────────────────────

@respx.mock
def test_connectors_create(client):
    respx.post(f"{BASE}/connectors").mock(return_value=httpx.Response(201, json=envelope({
        "id": "c1", "name": "Prod S3", "type": "s3",
        "active": True, "created_at": "2026-05-24",
    })))
    conn = client.connectors.create(
        "Prod S3", "s3",
        {"bucket": "my-bucket", "region": "eu-central-1",
         "access_key_id": "AKIA...", "secret_access_key": "secret"},
    )
    assert conn.id == "c1"
    assert conn.type == "s3"


def test_connectors_create_invalid_type(client):
    with pytest.raises(ValueError, match="Unknown connector type"):
        client.connectors.create("Bad", "ftp", {})


@respx.mock
def test_connectors_create_google_drive(client):
    respx.post(f"{BASE}/connectors").mock(return_value=httpx.Response(201, json=envelope({
        "id": "c2", "name": "Shared Invoices", "type": "google_drive",
        "active": True, "created_at": "2026-07-21",
    })))
    conn = client.connectors.create(
        "Shared Invoices", "google_drive",
        {"folder_id": "1a2B3cD4eFgH5iJkL6mN7oP8qR9sT0uV", "credentials_json": "{}"},
    )
    assert conn.id == "c2"
    assert conn.type == "google_drive"


@respx.mock
def test_connectors_create_pinecone(client):
    respx.post(f"{BASE}/connectors").mock(return_value=httpx.Response(201, json=envelope({
        "id": "c3", "name": "Prod Pinecone", "type": "pinecone",
        "active": True, "created_at": "2026-07-21",
    })))
    conn = client.connectors.create(
        "Prod Pinecone", "pinecone",
        {"api_key": "pc-key", "index_name": "flexorch-idx"},
    )
    assert conn.id == "c3"
    assert conn.type == "pinecone"


@respx.mock
def test_connectors_create_qdrant(client):
    respx.post(f"{BASE}/connectors").mock(return_value=httpx.Response(201, json=envelope({
        "id": "c4", "name": "Prod Qdrant", "type": "qdrant",
        "active": True, "created_at": "2026-07-21",
    })))
    conn = client.connectors.create(
        "Prod Qdrant", "qdrant",
        {"url": "https://xyz.qdrant.io:6333", "collection_name": "flexorch_chunks"},
    )
    assert conn.id == "c4"
    assert conn.type == "qdrant"


@respx.mock
def test_connectors_create_pgvector_external(client):
    respx.post(f"{BASE}/connectors").mock(return_value=httpx.Response(201, json=envelope({
        "id": "c5", "name": "Customer PG", "type": "pgvector_external",
        "active": True, "created_at": "2026-07-21",
    })))
    conn = client.connectors.create(
        "Customer PG", "pgvector_external",
        {"connection_string": "postgresql://user:pass@host:5432/db"},
    )
    assert conn.id == "c5"
    assert conn.type == "pgvector_external"


@respx.mock
def test_connectors_list(client):
    respx.get(f"{BASE}/connectors").mock(return_value=httpx.Response(200, json=envelope({
        "items": [
            {"id": "c1", "name": "Prod S3", "type": "s3", "active": True, "created_at": ""},
            {"id": "c2", "name": "Staging S3", "type": "s3", "active": True, "created_at": ""},
        ]
    })))
    connectors = client.connectors.list()
    assert len(connectors) == 2
    assert connectors[0].name == "Prod S3"


@respx.mock
def test_connectors_get(client):
    respx.get(f"{BASE}/connectors/c1").mock(return_value=httpx.Response(200, json=envelope({
        "id": "c1", "name": "Prod S3", "type": "s3",
        "active": True, "last_tested_at": "2026-05-24T10:00:00Z", "created_at": "",
    })))
    conn = client.connectors.get("c1")
    assert conn.last_tested_at == "2026-05-24T10:00:00Z"


@respx.mock
def test_connectors_delete(client):
    respx.delete(f"{BASE}/connectors/c1").mock(return_value=httpx.Response(204))
    client.connectors.delete("c1")


@respx.mock
def test_connectors_test_success(client):
    respx.post(f"{BASE}/connectors/c1/test").mock(return_value=httpx.Response(200, json=envelope({
        "success": True, "latency_ms": 42, "message": "Connection OK",
    })))
    result = client.connectors.test("c1")
    assert result.success is True
    assert result.latency_ms == 42


@respx.mock
def test_connectors_test_failure(client):
    respx.post(f"{BASE}/connectors/c1/test").mock(return_value=httpx.Response(200, json=envelope({
        "success": False, "latency_ms": None, "message": "Access Denied",
    })))
    result = client.connectors.test("c1")
    assert result.success is False
    assert result.message == "Access Denied"


# ── Connector schedules ────────────────────────────────────────────────────────

@respx.mock
def test_connectors_create_schedule(client):
    route = respx.post(f"{BASE}/connectors/c1/schedules").mock(return_value=httpx.Response(201, json=envelope({
        "id": "s1", "connector_id": "c1", "cron_expression": "0 2 * * *",
        "prefix_filter": "invoices/", "is_active": True,
        "last_run_at": None, "next_run_at": "2026-08-18T02:00:00Z", "created_at": "2026-08-17",
    })))
    sched = client.connectors.create_schedule("c1", "0 2 * * *", prefix_filter="invoices/")
    assert sched.id == "s1"
    assert sched.cron_expression == "0 2 * * *"
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["prefix_filter"] == "invoices/"


@respx.mock
def test_connectors_list_schedules(client):
    respx.get(f"{BASE}/connectors/c1/schedules").mock(return_value=httpx.Response(200, json=envelope([
        {"id": "s1", "connector_id": "c1", "cron_expression": "0 2 * * *", "prefix_filter": None, "is_active": True},
    ])))
    schedules = client.connectors.list_schedules("c1")
    assert len(schedules) == 1


@respx.mock
def test_connectors_delete_schedule(client):
    respx.delete(f"{BASE}/connectors/c1/schedules/s1").mock(
        return_value=httpx.Response(200, json=envelope({"deleted": True}))
    )
    client.connectors.delete_schedule("c1", "s1")


@respx.mock
def test_connectors_trigger_schedule(client):
    respx.post(f"{BASE}/connectors/c1/schedules/s1/trigger").mock(return_value=httpx.Response(202, json=envelope({
        "id": "log1", "schedule_id": "s1", "started_at": "2026-08-17T10:00:00Z",
        "completed_at": None, "files_found": 0, "files_new": 0, "files_skipped": 0,
        "files_failed": 0, "status": "running",
    })))
    log = client.connectors.trigger_schedule("c1", "s1")
    assert log.status == "running"


@respx.mock
def test_connectors_schedule_logs(client):
    respx.get(f"{BASE}/connectors/c1/schedules/s1/logs").mock(return_value=httpx.Response(200, json=envelope([
        {"id": "log1", "schedule_id": "s1", "started_at": "2026-08-17T02:00:00Z",
         "completed_at": "2026-08-17T02:01:00Z", "files_found": 5, "files_new": 3,
         "files_skipped": 2, "files_failed": 0, "status": "completed"},
    ])))
    logs = client.connectors.schedule_logs("c1", "s1")
    assert len(logs) == 1
    assert logs[0].files_new == 3


# ── process_from_s3 ────────────────────────────────────────────────────────────

@respx.mock
def test_process_from_s3_single(client):
    respx.post(f"{BASE}/data-process/async").mock(return_value=httpx.Response(202, json=accepted({
        "accepted": 1, "rejected": [],
        "jobs": [{"filename": "invoices/2026/inv-001.pdf", "job_id": "j-s3-1", "status": "queued"}],
    })))
    jobs = client.process_from_s3("c1", ["invoices/2026/inv-001.pdf"])
    assert len(jobs) == 1
    assert jobs[0].id == "j-s3-1"


@respx.mock
def test_process_from_s3_multiple_keys(client):
    respx.post(f"{BASE}/data-process/async").mock(return_value=httpx.Response(202, json=accepted({
        "accepted": 1, "rejected": [],
        "jobs": [{"filename": "x", "job_id": "j-s3-x", "status": "queued"}],
    })))
    jobs = client.process_from_s3("c1", ["a.pdf", "b.pdf", "c.pdf"])
    assert len(jobs) == 3


# ── dataset.export_to_s3 ───────────────────────────────────────────────────────

@respx.mock
def test_dataset_export_to_s3(client):
    respx.post(f"{BASE}/datasets/d1/export-s3").mock(return_value=httpx.Response(200, json=envelope({
        "s3_key": "exports/datasets/my-ds.jsonl", "size_bytes": 10240,
    })))
    ds = Dataset(id="d1", name="My DS", slug="my-ds", status="ready", _transport=client._transport)
    result = ds.export_to_s3("c1", "jsonl", prefix="exports/datasets/")
    assert result["s3_key"] == "exports/datasets/my-ds.jsonl"
    assert result["size_bytes"] == 10240


def test_dataset_export_to_s3_invalid_format(client):
    ds = Dataset(id="d1", name="My DS", slug="my-ds", status="ready", _transport=client._transport)
    with pytest.raises(ValueError, match="Unsupported format"):
        ds.export_to_s3("c1", "pdf")


# ── dataset.index + index_status ──────────────────────────────────────────────

@respx.mock
def test_dataset_index(client):
    respx.post(f"{BASE}/datasets/d1/index").mock(return_value=httpx.Response(202, json=envelope({
        "status": "indexing", "message": "Indexing started",
    })))
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    result = ds.index()
    assert result["status"] == "indexing"


@respx.mock
def test_dataset_index_status(client):
    respx.get(f"{BASE}/datasets/d1/index/status").mock(return_value=httpx.Response(200, json=envelope({
        "status": "ready", "chunks_indexed": 48, "total_chunks": 48,
    })))
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    status = ds.index_status()
    assert status["status"] == "ready"
    assert status["chunks_indexed"] == 48


# ── client.search ──────────────────────────────────────────────────────────────

@respx.mock
def test_search_basic(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json=envelope({
        "results": [
            {
                "chunk_id": "ch-1", "text": "Invoice total: 1200 EUR",
                "score": 0.92, "dataset_id": "d1",
                "chunk_index": 0, "token_count": 12, "metadata": {},
            },
        ]
    })))
    results = client.search("invoice amount")
    assert len(results) == 1
    assert results[0].score == 0.92
    assert results[0].dataset_id == "d1"


@respx.mock
def test_search_with_filters(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json=envelope({
        "results": []
    })))
    results = client.search(
        "tax declaration",
        top_k=5,
        filters={"document_type": "tax_declaration", "language": "de"},
    )
    assert results == []


@respx.mock
def test_search_returns_empty_on_no_results(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json=envelope({})))
    results = client.search("nothing")
    assert results == []
