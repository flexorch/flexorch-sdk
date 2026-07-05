"""RAG helpers for the FlexOrch SDK.

FlexOrchRetriever  — LangChain-compatible retriever backed by /v1/search.
FlexOrchReader     — LlamaIndex-compatible reader backed by /v1/datasets/{id}/chunks.

Both classes work without LangChain or LlamaIndex installed.
They return RAGDocument objects that are duck-type compatible with:
  - langchain_core.documents.Document  (page_content + metadata)
  - llama_index.core.schema.Document   (.text property + metadata)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import FlexOrchClient

_GRADE_ORDER: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}


def _grade_and_above(threshold: str) -> list[str]:
    """Return all grades at or above *threshold*. E.g. "B" → ["A", "B"]."""
    t = _GRADE_ORDER.get(threshold.upper(), 3)
    return [g for g, rank in _GRADE_ORDER.items() if rank <= t]


@dataclass
class RAGDocument:
    """A text chunk with metadata.

    Duck-type compatible with both LangChain Document and LlamaIndex Document.

    Attributes:
        page_content: Chunk text (LangChain-style attribute name).
        metadata:     Dict of chunk metadata.
    """

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """LlamaIndex-style alias for page_content."""
        return self.page_content

    def __repr__(self) -> str:
        snippet = self.page_content[:60].replace("\n", " ")
        return f"RAGDocument(text={snippet!r}, metadata={self.metadata})"


class FlexOrchRetriever:
    """LangChain-compatible retriever backed by FlexOrch's /v1/search endpoint.

    Works without LangChain installed — ``invoke()`` returns :class:`RAGDocument`
    objects that are duck-type compatible with ``langchain_core.documents.Document``.

    Example::

        from flexorch_sdk import FlexOrchClient
        from flexorch_sdk.rag import FlexOrchRetriever

        client = FlexOrchClient("dfx_xxx")
        retriever = FlexOrchRetriever(client, quality_threshold="B", pii_masked=True)

        # standalone
        docs = retriever.invoke("payment terms")

        # LangChain chain
        from langchain.chains import RetrievalQA
        qa = RetrievalQA.from_chain_type(llm=your_llm, retriever=retriever)
    """

    def __init__(
        self,
        client: "FlexOrchClient",
        *,
        quality_threshold: str = "B",
        pii_masked: bool | None = None,
        top_k: int = 5,
        document_type: str | None = None,
        language: str | None = None,
        mode: str = "auto",
    ) -> None:
        if quality_threshold.upper() not in _GRADE_ORDER:
            raise ValueError(
                f"quality_threshold must be A, B, C, or D — got {quality_threshold!r}"
            )
        self._client = client
        self._quality_threshold = quality_threshold.upper()
        self._pii_masked = pii_masked
        self._top_k = top_k
        self._document_type = document_type
        self._language = language
        self._mode = mode

    def invoke(self, query: str, **_: Any) -> list[RAGDocument]:
        """Retrieve the most relevant chunks for *query*.

        Requests 2× top_k results from the API then filters client-side by
        quality threshold, returning at most top_k final documents.

        Returns:
            List of :class:`RAGDocument` ordered by descending relevance score.
        """
        filters: dict[str, Any] = {}
        if self._pii_masked is not None:
            filters["pii_masked"] = self._pii_masked
        if self._document_type:
            filters["document_type"] = self._document_type
        if self._language:
            filters["language"] = self._language

        raw = self._client.search(
            query,
            top_k=min(self._top_k * 2, 50),
            mode=self._mode,
            filters=filters or None,
        )

        allowed_grades = set(_grade_and_above(self._quality_threshold))
        docs: list[RAGDocument] = []
        for r in raw:
            grade = r.metadata.get("quality_grade", "D")
            if grade not in allowed_grades:
                continue
            docs.append(
                RAGDocument(
                    page_content=r.text,
                    metadata={
                        "chunk_id": r.chunk_id,
                        "dataset_id": r.dataset_id,
                        "score": r.score,
                        "quality_grade": grade,
                        "pii_masked": r.metadata.get("pii_masked"),
                        "doc_type": r.metadata.get("doc_type"),
                        "language": r.metadata.get("language"),
                    },
                )
            )
            if len(docs) >= self._top_k:
                break
        return docs

    # LangChain BaseRetriever compatibility shims
    def get_relevant_documents(self, query: str) -> list[RAGDocument]:
        return self.invoke(query)

    async def aget_relevant_documents(self, query: str) -> list[RAGDocument]:
        return self.invoke(query)

    def __repr__(self) -> str:
        return (
            f"FlexOrchRetriever("
            f"quality_threshold={self._quality_threshold!r}, "
            f"top_k={self._top_k}, "
            f"mode={self._mode!r})"
        )


class FlexOrchReader:
    """LlamaIndex-compatible document reader backed by FlexOrch chunk API.

    Paginates through all RAG chunks of a processed, indexed dataset.
    Works without LlamaIndex installed — returns :class:`RAGDocument` objects
    that are duck-type compatible with ``llama_index.core.schema.Document``.

    Example::

        from flexorch_sdk import FlexOrchClient
        from flexorch_sdk.rag import FlexOrchReader

        reader = FlexOrchReader(FlexOrchClient("dfx_xxx"))
        documents = reader.load_data("42", min_quality="B")

        # LlamaIndex VectorStoreIndex
        from llama_index.core import VectorStoreIndex
        index = VectorStoreIndex.from_documents(documents)
    """

    def __init__(self, client: "FlexOrchClient") -> None:
        self._client = client

    def load_data(
        self,
        dataset_id: str | int,
        *,
        min_quality: str = "B",
        pii_masked_only: bool = False,
        page_size: int = 100,
    ) -> list[RAGDocument]:
        """Load all qualifying chunks from a dataset.

        Paginates automatically until all matching chunks are retrieved.

        Args:
            dataset_id:      ID of the indexed dataset.
            min_quality:     Minimum quality grade to include (A/B/C/D). Default: ``"B"``.
            pii_masked_only: When True, include only chunks where PII was masked.
            page_size:       Chunks per page (max 100). Default: 100.

        Returns:
            List of :class:`RAGDocument`, one per chunk.
        """
        if min_quality.upper() not in _GRADE_ORDER:
            raise ValueError(
                f"min_quality must be A, B, C, or D — got {min_quality!r}"
            )

        grade_filter = ",".join(_grade_and_above(min_quality))
        all_docs: list[RAGDocument] = []
        page = 1

        while True:
            data = (
                self._client._transport.get(
                    f"/datasets/{dataset_id}/chunks",
                    params={
                        "page": page,
                        "page_size": page_size,
                        "quality_grade": grade_filter,
                        **({"pii_masked": "true"} if pii_masked_only else {}),
                    },
                )
                or {}
            )
            items: list[dict[str, Any]] = data.get("items", [])
            total: int = data.get("total", 0)

            for item in items:
                meta: dict[str, Any] = item.get("metadata") or {}
                all_docs.append(
                    RAGDocument(
                        page_content=item.get("text", ""),
                        metadata={
                            "chunk_id": item.get("chunk_id"),
                            "chunk_index": item.get("chunk_index"),
                            "dataset_id": str(dataset_id),
                            "doc_type": meta.get("doc_type"),
                            "language": meta.get("language"),
                            "quality_grade": meta.get("quality_grade"),
                            "quality_score": meta.get("quality_score"),
                            "pii_masked": meta.get("pii_masked"),
                            "source": meta.get("source_filename"),
                        },
                    )
                )

            if len(all_docs) >= total or len(items) < page_size:
                break
            page += 1

        return all_docs

    def __repr__(self) -> str:
        return "FlexOrchReader()"
