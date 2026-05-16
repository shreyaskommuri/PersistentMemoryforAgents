from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import MemoryEntry, MemorySearchResult, MemoryType, ScoreBreakdown

# Exponential decay rate per hour. Half-life ≈ 6.9 hours.
_DECAY_LAMBDA = 0.1


def recency_score(entry: MemoryEntry) -> float:
    """Exponential decay based on hours since last access."""
    now = datetime.now(timezone.utc)
    accessed = entry.accessed_at
    if accessed.tzinfo is None:
        accessed = accessed.replace(tzinfo=timezone.utc)
    age_hours = (now - accessed).total_seconds() / 3600.0
    return math.exp(-_DECAY_LAMBDA * age_hours)


def composite_score(entry: MemoryEntry, semantic_sim: float = 0.0) -> float:
    """
    Blend four signals into a single score in [0, 1].
    Weights: semantic=0.4, importance=0.3, recency=0.2, frequency=0.1.
    """
    r = recency_score(entry)
    freq = min(math.log1p(entry.access_count) / 10.0, 1.0)
    return 0.4 * semantic_sim + 0.3 * entry.importance + 0.2 * r + 0.1 * freq


def build_score_breakdown(entry: MemoryEntry, semantic_sim: float = 0.0) -> ScoreBreakdown:
    """Return the full per-component score breakdown for a memory."""
    r = recency_score(entry)
    freq = min(math.log1p(entry.access_count) / 10.0, 1.0)
    now = datetime.now(timezone.utc)
    accessed = entry.accessed_at
    if accessed.tzinfo is None:
        accessed = accessed.replace(tzinfo=timezone.utc)
    age_hours = (now - accessed).total_seconds() / 3600.0
    total = 0.4 * semantic_sim + 0.3 * entry.importance + 0.2 * r + 0.1 * freq
    return ScoreBreakdown(
        semantic_sim=round(semantic_sim, 4),
        importance=round(entry.importance, 4),
        recency=round(r, 4),
        access_frequency=round(freq, 4),
        composite=round(total, 4),
        age_hours=round(age_hours, 2),
    )


class Retriever:
    def search(
        self,
        query: str,
        corpus: list[MemoryEntry],
        tags: Optional[list[str]] = None,
        memory_types: Optional[list[MemoryType]] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        candidates = corpus

        if memory_types:
            candidates = [e for e in candidates if e.memory_type in memory_types]

        if tags:
            tag_set = {t.lower() for t in tags}
            candidates = [
                e for e in candidates if tag_set.intersection(t.lower() for t in e.tags)
            ]

        if not candidates:
            return []

        sims = self._tfidf_similarities(query, candidates)

        results = []
        for entry, sim in zip(candidates, sims):
            score = composite_score(entry, float(sim))
            if score >= min_score:
                results.append(MemorySearchResult(memory=entry, score=round(score, 4)))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    @staticmethod
    def _tfidf_similarities(query: str, entries: list[MemoryEntry]) -> np.ndarray:
        texts = [e.content for e in entries]
        try:
            vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
            matrix = vectorizer.fit_transform(texts + [query])
            sims = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
        except ValueError:
            # Corpus too small or all stop words — fall back to zeros.
            sims = np.zeros(len(entries))
        return sims
