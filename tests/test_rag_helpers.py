"""Tests for flexorch_sdk.rag — FlexOrchRetriever, FlexOrchReader, dataset.chunks()."""
import pytest
import respx
import httpx

from flexorch_sdk import FlexOrchClient, RAGDocument, FlexOrchRetriever, FlexOrchReader
from flexorch_sdk.models.dataset import Dataset
from flexorch_sdk.rag import _grade_and_above

BASE = "https://api.flexorch.com/v1"

CHUNK_ITEM = {
    "chunk_id": "ch-1",
    "chunk_index": 0,
    "text": "Invoice total: 1200 EUR",
    "token_count": 8,
    "metadata": {
        "quality_grade": "A",
        "quality_score": 0.91,
        "pii_masked": False,
        "doc_type": "invoice",
        "language": "en",
        "source_filename": "inv-001.pdf",
    },
}

SEARCH_RESULT = {
    "chunk_id": "ch-1",
    "text": "Invoice total: 1200 EUR",
    "score": 0.92,
    "dataset_id": "d1",
    "chunk_index": 0,
    "token_count": 8,
    "metadata": {"quality_grade": "A", "pii_masked": False, "doc_type": "invoice"},
}


@pytest.fixture
def client():
    return FlexOrchClient("fx_test", base_url=BASE)


# ── _grade_and_above helper ───────────────────────────────────────────────────

def test_grade_and_above_a():
    assert _grade_and_above("A") == ["A"]

def test_grade_and_above_b():
    assert set(_grade_and_above("B")) == {"A", "B"}

def test_grade_and_above_c():
    assert set(_grade_and_above("C")) == {"A", "B", "C"}

def test_grade_and_above_d():
    assert set(_grade_and_above("D")) == {"A", "B", "C", "D"}


# ── dataset.chunks() ─────────────────────────────────────────────────────────

@respx.mock
def test_dataset_chunks_basic(client):
    respx.get(f"{BASE}/datasets/d1/chunks").mock(return_value=httpx.Response(200, json={
        "items": [CHUNK_ITEM],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }))
    ds = Dataset(id="d1", name="test", slug="test", status="ready", _transport=client._transport)
    result = ds.chunks()
    assert result["total"] == 1
    assert result["items"][0]["chunk_id"] == "ch-1"


@respx.mock
def test_dataset_chunks_with_filters(client):
    route = respx.get(f"{BASE}/datasets/d1/chunks").mock(return_value=httpx.Response(200, json={
        "items": [], "total": 0, "page": 1, "page_size": 20,
    }))
    ds = Dataset(id="d1", name="test", slug="test", status="ready", _transport=client._transport)
    ds.chunks(quality_grade="A,B", pii_masked=True)
    assert route.called


# ── FlexOrchRetriever ─────────────────────────────────────────────────────────

def test_retriever_invalid_threshold(client):
    with pytest.raises(ValueError, match="quality_threshold must be"):
        FlexOrchRetriever(client, quality_threshold="X")


def test_retriever_repr(client):
    r = FlexOrchRetriever(client, quality_threshold="A", top_k=3)
    assert "FlexOrchRetriever" in repr(r)
    assert "A" in repr(r)


@respx.mock
def test_retriever_invoke_basic(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={
        "results": [SEARCH_RESULT],
    }))
    retriever = FlexOrchRetriever(client)
    docs = retriever.invoke("invoice amount")
    assert len(docs) == 1
    assert isinstance(docs[0], RAGDocument)
    assert docs[0].page_content == "Invoice total: 1200 EUR"
    assert docs[0].metadata["score"] == 0.92
    assert docs[0].metadata["dataset_id"] == "d1"


@respx.mock
def test_retriever_grade_filter_excludes_low_grade(client):
    low_grade_result = {**SEARCH_RESULT, "metadata": {"quality_grade": "D"}}
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={
        "results": [low_grade_result],
    }))
    retriever = FlexOrchRetriever(client, quality_threshold="B")
    docs = retriever.invoke("anything")
    assert docs == []


@respx.mock
def test_retriever_grade_filter_allows_equal_grade(client):
    b_grade_result = {**SEARCH_RESULT, "metadata": {"quality_grade": "B"}}
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={
        "results": [b_grade_result],
    }))
    retriever = FlexOrchRetriever(client, quality_threshold="B")
    docs = retriever.invoke("anything")
    assert len(docs) == 1


@respx.mock
def test_retriever_get_relevant_documents_compat(client):
    respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={
        "results": [SEARCH_RESULT],
    }))
    retriever = FlexOrchRetriever(client)
    docs = retriever.get_relevant_documents("test")
    assert len(docs) == 1


# ── FlexOrchReader ────────────────────────────────────────────────────────────

def test_reader_repr(client):
    assert repr(FlexOrchReader(client)) == "FlexOrchReader()"


def test_reader_invalid_min_quality(client):
    with pytest.raises(ValueError, match="min_quality must be"):
        FlexOrchReader(client).load_data("42", min_quality="Z")


@respx.mock
def test_reader_load_data_single_page(client):
    respx.get(f"{BASE}/datasets/42/chunks").mock(return_value=httpx.Response(200, json={
        "items": [CHUNK_ITEM],
        "total": 1,
        "page": 1,
        "page_size": 100,
    }))
    reader = FlexOrchReader(client)
    docs = reader.load_data("42")
    assert len(docs) == 1
    assert isinstance(docs[0], RAGDocument)
    assert docs[0].text == "Invoice total: 1200 EUR"
    assert docs[0].metadata["chunk_id"] == "ch-1"
    assert docs[0].metadata["dataset_id"] == "42"
    assert docs[0].metadata["quality_grade"] == "A"


@respx.mock
def test_reader_load_data_paginated(client):
    page1 = {
        "items": [CHUNK_ITEM] * 2,
        "total": 3,
        "page": 1,
        "page_size": 2,
    }
    page2 = {
        "items": [CHUNK_ITEM],
        "total": 3,
        "page": 2,
        "page_size": 2,
    }
    respx.get(f"{BASE}/datasets/42/chunks").mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
    )
    reader = FlexOrchReader(client)
    docs = reader.load_data("42", page_size=2)
    assert len(docs) == 3


@respx.mock
def test_reader_pii_masked_only(client):
    route = respx.get(f"{BASE}/datasets/42/chunks").mock(return_value=httpx.Response(200, json={
        "items": [], "total": 0, "page": 1, "page_size": 100,
    }))
    FlexOrchReader(client).load_data("42", pii_masked_only=True)
    assert route.called


# ── client.search with mode ───────────────────────────────────────────────────

@respx.mock
def test_search_mode_passed(client):
    route = respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={
        "results": [],
    }))
    client.search("query", mode="semantic")
    assert route.called
    sent = route.calls[0].request
    import json
    body = json.loads(sent.content)
    assert body["mode"] == "semantic"


@respx.mock
def test_search_default_mode_is_auto(client):
    route = respx.post(f"{BASE}/search").mock(return_value=httpx.Response(200, json={"results": []}))
    client.search("query")
    body = __import__("json").loads(route.calls[0].request.content)
    assert body["mode"] == "auto"
