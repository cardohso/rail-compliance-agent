"""`search_regulation`: find the passages of EU rail law that answer a question.

One interface, three ways to reach the rail assistant (cardohso/rail-regulation-rag):

- `LocalBackend`: its retrieval run in-process (same embedder, same Qdrant index, hybrid
  BM25 + vector search), with no LLM and no network. Used for evaluation, so a run does not
  spend the live demo's quota. Needs the optional `local` dependency group.
- `LiveBackend`: its deployed `POST /ask`, which also returns a generated answer and refuses
  when it cannot ground one. Rate-limited by the demo, so it retries with backoff.
- `ReplayBackend`: recorded results from a JSON file, for offline tests.

`CachingBackend` wraps any of them with a disk cache keyed by backend, k and question.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import random
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import httpx

from rail_compliance.models import Passage, SearchResult

MIN_QUESTION, MAX_QUESTION = 3, 500  # the live API rejects anything outside this
RETRYABLE = {429, 502, 503, 504}


class SearchError(RuntimeError):
    """The rail assistant could not be reached or kept refusing the request."""


class SearchBackend(Protocol):
    name: str

    def search(self, question: str, k: int) -> SearchResult: ...


def search_regulation(question: str, backend: SearchBackend, k: int = 8) -> SearchResult:
    question = " ".join(question.split())
    if not MIN_QUESTION <= len(question) <= MAX_QUESTION:
        raise ValueError(f"question must be {MIN_QUESTION}-{MAX_QUESTION} characters")
    return backend.search(question, k)


class LocalBackend:
    """Wraps a `retrieve(question, k) -> passages` function. Build the real one with
    `from_rail_rag`; tests pass a fake."""

    name = "local"

    def __init__(self, retrieve: Callable[[str, int], list[Passage]]):
        self._retrieve = retrieve

    def search(self, question: str, k: int) -> SearchResult:
        return SearchResult(
            question=question, passages=self._retrieve(question, k), backend=self.name
        )

    @classmethod
    def from_rail_rag(cls, data_dir: Path) -> LocalBackend:
        """Retrieval from an installed `rail_rag`, reading its corpus and index from `data_dir`
        (a rail-regulation-rag `data/` folder with the index built: `python -m rail_rag.index`)."""
        # rail_rag reads its data location at import time, so set it before importing it.
        os.environ.setdefault("RAIL_RAG_DATA_DIR", str(Path(data_dir).expanduser().resolve()))
        try:
            from rail_rag.citations import format_citations
            from rail_rag.config import Settings
            from rail_rag.embeddings import LocalEmbedder
            from rail_rag.vectorstore import make_store
        except ImportError as exc:
            raise SearchError(
                "the local backend needs rail_rag: run `uv sync --group local`"
            ) from exc

        settings = Settings(vector_store="qdrant", search_mode="hybrid")
        if not (settings.qdrant_path / "meta.json").exists():
            raise SearchError(
                f"no vector index at {settings.qdrant_path}: build it with "
                "`RAIL_RAG_DATA_DIR=<data dir> uv run python -m rail_rag.index`"
            )
        embedder, store = LocalEmbedder(settings.embedding_model), make_store(settings)

        def retrieve(question: str, k: int) -> list[Passage]:
            hits = store.search(embedder.embed_query(question), k=k, text=question)
            return [
                Passage(
                    id=c.passage_id,
                    doc_id=c.doc_id,
                    document=c.document,
                    section=c.section,
                    heading=c.heading,
                    text=c.passage,
                    url=c.url,
                    score=c.score,
                )
                for c in format_citations(hits)
            ]

        return cls(retrieve)


class LiveBackend:
    """The deployed rail assistant. Its generated answer and refusal come back with the
    passages it cited (at most five, after its own grading)."""

    name = "live"

    def __init__(
        self,
        base_url: str,
        client: httpx.Client | None = None,
        *,
        attempts: int = 6,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.url = base_url.rstrip("/") + "/ask"
        self.client = client or httpx.Client(timeout=60.0)
        self.attempts, self.base_delay, self.max_delay, self.sleep = (
            attempts,
            base_delay,
            max_delay,
            sleep,
        )

    def _post(self, question: str) -> dict:
        last = ""
        for attempt in range(self.attempts):
            retry_after = None
            try:
                response = self.client.post(self.url, json={"question": question})
            except httpx.TransportError as exc:
                last = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    return response.json()
                if response.status_code not in RETRYABLE:
                    raise SearchError(
                        f"{self.url} returned {response.status_code}: {response.text}"
                    )
                last = f"HTTP {response.status_code}"
                with contextlib.suppress(KeyError, ValueError):
                    retry_after = float(response.headers["retry-after"])
            if attempt == self.attempts - 1:
                break
            delay = retry_after or min(self.max_delay, self.base_delay * 2**attempt)
            self.sleep(delay * random.uniform(0.9, 1.1))
        raise SearchError(f"gave up after {self.attempts} attempts: {last}")

    def search(self, question: str, k: int) -> SearchResult:
        body = self._post(question)  # k is fixed by the server; kept for interface parity
        passages = [
            Passage(
                id=c["passage_id"],
                doc_id=c["doc_id"],
                document=c["document"],
                section=c["section"],
                heading=c.get("heading", ""),
                text=c["passage"],
                url=c.get("url", ""),
                score=c.get("score", 0.0),
            )
            for c in body["citations"]
        ]
        return SearchResult(
            question=question,
            passages=passages,
            backend=self.name,
            answer=body["answer"],
            refused=bool(body["refused"]),
        )


class ReplayMiss(SearchError):
    """The recorded results have no entry for this question."""


class ReplayBackend:
    """Serves recorded results: a JSON file of {question: SearchResult}."""

    name = "replay"

    def __init__(self, results: dict[str, SearchResult]):
        self.results = results

    @classmethod
    def from_file(cls, path: Path) -> ReplayBackend:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls({q: SearchResult.model_validate(r) for q, r in raw.items()})

    def search(self, question: str, k: int) -> SearchResult:
        try:
            result = self.results[question]
        except KeyError:
            raise ReplayMiss(f"no recorded result for: {question!r}") from None
        return result.model_copy(update={"passages": result.passages[:k]})


class CachingBackend:
    """Disk cache around another backend, so a re-run costs no retrieval and no live calls."""

    def __init__(self, inner: SearchBackend, cache_dir: Path):
        self.inner, self.cache_dir = inner, Path(cache_dir)
        self.name = inner.name
        self.hits = self.misses = 0

    def _path(self, question: str, k: int) -> Path:
        key = hashlib.sha256(f"{self.inner.name}\0{k}\0{question}".encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def search(self, question: str, k: int) -> SearchResult:
        path = self._path(question, k)
        if path.exists():
            self.hits += 1
            return SearchResult.model_validate_json(path.read_text(encoding="utf-8"))
        self.misses += 1
        result = self.inner.search(question, k)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=1), encoding="utf-8")
        return result
