from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    dataset_id: str
    chunk_index: int
    token_count: int
    metadata: dict = field(default_factory=dict)

    @classmethod
    def _from_dict(cls, data: dict) -> SearchResult:
        return cls(
            chunk_id=data.get("chunk_id", ""),
            text=data.get("text", ""),
            score=data.get("score", 0.0),
            dataset_id=data.get("dataset_id", ""),
            chunk_index=data.get("chunk_index", 0),
            token_count=data.get("token_count", 0),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"SearchResult(score={self.score:.3f}, dataset_id={self.dataset_id!r}, chunk_index={self.chunk_index})"
