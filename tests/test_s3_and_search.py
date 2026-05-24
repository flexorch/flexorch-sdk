"""Tests for ConnectorsResource, process_from_s3, dataset.export_to_s3, client.search."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient, Connector, ConnectorTestResult, SearchResult
from flexorch_sdk.models.dataset import Dataset

BASE = "https://api.flexorch.com/v1"


@pytest.fixture
def client():
    return FlexOrchClient("fx_test", base_url=BASE)


# ── ConnectorsResource ─────────────────────────────────────────────────────────

@respx.mock
def test_connectors_create(client):
    respx.post(f"{BASE}/connectors").mock(return_value=httpx.Response(201, json={
        "id": "c1", "name": "Prod S3", "type": "s3",
        "active": True, "created_at": "2026-05-24",
    }))
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
def test_connectors_list(client):
    respx.get(f"{BASE}/connectors").mock(return_value=httpx.Response(200, json={
        "items": [
            {"id": "c1", "name": "Prod S3", "type": "s3", "active": True, "created_at": ""},
            {"id": "c2", "name": "Staging S3", "type": "s3", "active": True, "created_at": ""},
        ]
    }))
    connectors = client.connectors.list()
    assert len(connectors) == 2
    assert connectors[0].name == "Prod S3"


@respx.mock
def test_connectors_get(client):
    respx.get(f"{BASE}/connectors/c1").mock(return_value=httpx.Response(200, json={
        "id": "c1", "name": "Prod S3", "type": "s3",
        "active": True, "last_tested_at": "2026-05-24T10:00:00Z", "created_at": "",
    }))
    conn = client.connectors.get("c1")
    assert conn.last_tested_at == "2026-05-24T10:00:00Z"


@respx.mock
def test_connectors_delete(client):
    respx.delete(f"{BASE}/connectors/c1").mock(return_value=httpx.Response(204))
    client.connectors.delete("c1")


@respx.mock
def test_connectors_test_success(client):
    respx.post(f"{BASE}/connectors/c1/test").mock(return_value=httpx.Response(200, json={
        "success": True, "latency_ms": 42, "message": "Connection OK",
    }))
    result = client.connectors.test("c1")
    assert result.success is True
    assert result.latency_ms == 42


@respx.mock
def test_connectors_test_failure(client):
    respx.post(f"{BASE}/connectors/c1/test").mock(return_value=httpx.Response(200, json={
        "success": False, "latency_ms": None, "message": "Access Denied",
    }))
    result = client.connectors.test("c1")
    assert result.success is False
    assert result.message == "Access Denied"


# ── process_from_s3 ────────────────────────────────────────────────────────────

@respx.mock
def test_process_from_s3_single(client):
    respx.post(f"{BASE}/data-process/async").mock(return_value=httpx.Response(202, json={
        "job_id": "j-s3-1", "status": "queued",
    }))
    jobs = client.process_from_s3("c1", ["invoices/2026/inv-001.pdf"])
    assert len(jobs) == 1
    assert jobs[0].id == "j-s3-1"


@respx.mock
def test_process_from_s3_multiple_keys(client):
    respx.post(f"{BASE}/data-process/async").mock(return_value=httpx.Response(202, json={
        "job_id": "j-s3-x", "status": "queued",
    }))
    jobs = client.process_from_s3("c1", ["a.pdf", "b.pdf", "c.pdf"])
    assert len(jobs) == 3


# ── dataset.export_to_s3 ───────────────────────────────────────────────────────

@respx.mock
def test_dataset_export_to_s3(client):
    respx.post(f"{BASE}/datasets/d1/export-s3").mock(return_value=httpx.Response(200, json={
        "s3_key": "exports/datasets/my-ds.jsonl", "size_bytes": 10240,
    }))
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
    respx.post(f"{BASE}/datasets/d1/index").mock(return_value=httpx.Response(202, json={
        "status": "indexing", "message": "Indexing started",
    }))
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    result = ds.index()
    assert result["status"] == "indexing"


@respx.mock
def test_dataset_index_status(client):
    respx.get(f"{BASE}/datasets/d1/index/status").mock(return_value=httpx.Response(200, json={
        "status": "ready", "chunks_indexed": 48, "total_chunks": 48,
    }))
    ds = Dataset(id="d1", name="x", slug="x", status="ready", _transport=client._transport)
    status = ds.index_status()
    assert status["status"] == "ready"
    assert status["chunks_indexed"] == 48


# ── client.search ──────────────────────────────────────────────────────────────

@respx.mock
def test_search_basic(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={
        "results": [
            {
                "chunk_id": "ch-1", "text": "Invoice total: 1200 EUR",
                "score": 0.92, "dataset_id": "d1",
                "chunk_index": 0, "token_count": 12, "metadata": {},
            },
        ]
    }))
    results = client.search("invoice amount")
    assert len(results) == 1
    assert results[0].score == 0.92
    assert results[0].dataset_id == "d1"


@respx.mock
def test_search_with_filters(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={
        "results": []
    }))
    results = client.search(
        "tax declaration",
        top_k=5,
        filters={"document_type": "tax_declaration", "language": "de"},
    )
    assert results == []


@respx.mock
def test_search_returns_empty_on_no_results(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={}))
    results = client.search("nothing")
    assert results == []
