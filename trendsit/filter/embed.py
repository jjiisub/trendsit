"""임베딩 관련성 필터: 임베더(실제 / 모의), 관심사 프로필, 점수, 판정, 저장.

- 실제: sentence-transformers + Qwen3-Embedding(`embed` 선택 묶음). 쿼리(관심사 설명) 쪽에만 지시문을 붙인다(모델 카드 방식)
- 모의: 단어 해시 벡터. 네트워크와 큰 의존성 없이 테스트와 CI에서 쓴다(공유 단어가 많을수록 가깝다)
- 임베딩은 item_embeddings에 저장해 다시 계산하지 않는다. 벡터는 float32 BLOB(git에 넣지 않음, data/ 아래 DB)
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from array import array
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from ..core.config import FilterConfig
from ..core.db import DB, now_kst


class Embedder(Protocol):
    model_id: str
    device: str

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_docs(self, texts: Sequence[str]) -> list[list[float]]: ...


def normalize(v: Sequence[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """정규화된 벡터끼리의 코사인 = 내적."""
    return sum(x * y for x, y in zip(a, b, strict=True))


def to_blob(v: Sequence[float]) -> bytes:
    return array("f", v).tobytes()


def from_blob(b: bytes) -> list[float]:
    a = array("f")
    a.frombytes(b)
    return list(a)


_TOKEN = re.compile(r"[A-Za-z0-9]+|[가-힣]+")


class HashEmbedder:
    """모의 임베더. 영어는 단어, 한국어는 글자 2개씩 묶어(조사가 붙어도 겹치게) 해시 버킷에 센다."""

    model_id = "mock/hash-256"
    device = "cpu"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in _TOKEN.findall(text.lower()):
            grams = [tok] if tok.isascii() else ([tok[i:i + 2] for i in range(len(tok) - 1)] or [tok])
            for g in grams:
                h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=4).digest(), "big")
                v[h % self.dim] += 1.0
        return normalize(v)

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_docs(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class SentenceEmbedder:
    """실제 임베더: sentence-transformers(`uv sync --extra embed`). 장치는 mps → cuda → cpu 순으로 자동."""

    def __init__(self, model_id: str, instruction: str, device: str | None = None, batch_size: int = 16):
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # 선택 묶음이 없을 때 이유를 분명히
            raise RuntimeError("임베딩 묶음 없음: `uv sync --extra embed` 후 다시 실행(개발용은 --embedder mock)") from e
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id, self.device, self.batch_size = model_id, device, batch_size
        self.prompt = f"Instruct: {instruction}\nQuery: "
        self._model = SentenceTransformer(model_id, device=device)

    def _encode(self, texts: Sequence[str], prompt: str | None) -> list[list[float]]:
        vecs = self._model.encode(list(texts), prompt=prompt, batch_size=self.batch_size,
                                  normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        return [list(map(float, v)) for v in vecs]

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts, self.prompt)

    def embed_docs(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts, None)


def make_embedder(kind: str, cfg: FilterConfig) -> Embedder:
    if kind == "mock":
        return HashEmbedder()
    return SentenceEmbedder(cfg.model, cfg.instruction, batch_size=cfg.batch_size)


def library_versions() -> dict[str, str]:
    import importlib.metadata as md

    out = {}
    for name in ("sentence-transformers", "torch", "transformers"):
        try:
            out[name] = md.version(name)
        except md.PackageNotFoundError:
            out[name] = "없음"
    return out


# ---------- 입력, 점수, 판정 ----------
def doc_text(row: Any, doc_chars: int) -> str:
    """글 = 제목 + 요약 + 본문 앞 doc_chars자, 영상 = 제목 + 설명."""
    if row["channel"] == "video":
        parts = [row["title"], row["body"] or row["summary_feed"]]
    else:
        parts = [row["title"], row["summary_feed"], (row["body"] or "")[:doc_chars]]
    return "\n".join(p.strip() for p in parts if p and p.strip())


def best_interest(vec: Sequence[float], interests: list[tuple[str, list[float]]]) -> tuple[float, str]:
    """관심사 설명들과의 코사인 최댓값과 그 키워드 id."""
    score, kid = max((cosine(vec, q), k) for k, q in interests)
    return round(score, 6), kid


def decide(keyword_status: str, keyword_reason: str | None, score: float, cfg: FilterConfig) -> tuple[str, str]:
    """(decision, reason). 판정은 코드(설정의 문턱값 두 개). S1 키워드 판정은 바꾸지 않는다."""
    if keyword_status == "pass":
        return ("keep", "keyword_pass") if score >= cfg.drop_below else ("drop", "low_similarity")
    if keyword_reason and keyword_reason.startswith("excluded:"):
        return "drop", keyword_reason  # 제외어로 걸러진 것은 되살리지 않는다
    if score >= cfg.rescue_above:
        return "keep", "rescued"
    return "drop", keyword_reason or "no_keyword"


@dataclass
class FilterResult:
    run_id: str
    model: str
    device: str
    n: int = 0
    computed: int = 0  # 이번 실행에서 새로 계산한 임베딩 수(재사용하면 0)
    seconds: float = 0.0
    decisions: dict[str, int] = field(default_factory=dict)  # reason → 건수
    same_as: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)  # 리포트용 판정 목록

    def summary(self) -> str:
        keep = sum(1 for r in self.rows if r["decision"] == "keep")
        reasons = ", ".join(f"{k} {v}" for k, v in sorted(self.decisions.items()))
        return (f"{self.n}건(새 임베딩 {self.computed}, {self.seconds:.1f}초, {self.model}@{self.device}): "
                f"keep {keep}, drop {self.n - keep} [{reasons}], 같은 URL 연결 {self.same_as}")


def item_rows(db: DB, since: date | None, until: date | None) -> list[Any]:
    where, args = "", []
    if since:
        where += " AND i.day >= ?"
        args.append(since.isoformat())
    if until:
        where += " AND i.day <= ?"
        args.append(until.isoformat())
    return db.conn.execute(
        "SELECT i.id, i.source_id, i.channel, i.title, i.summary_feed, i.url, i.day, i.published_at, "
        "i.filter_status, i.filter_reason, t.text AS body FROM items i LEFT JOIN item_texts t ON t.item_id = i.id "
        f"WHERE i.channel IN ('text', 'video'){where} ORDER BY i.id", args).fetchall()


def embeddings_for(db: DB, embedder: Embedder, rows: list[Any], cfg: FilterConfig) -> tuple[dict[int, list[float]], int]:
    """저장된 임베딩(같은 모델, 같은 입력 해시)은 재사용하고 나머지만 계산해 저장한다."""
    texts = {r["id"]: doc_text(r, cfg.doc_chars) for r in rows}
    hashes = {i: hashlib.sha256(t.encode()).hexdigest()[:16] for i, t in texts.items()}
    have = {r["item_id"]: (r["text_hash"], r["vec"]) for r in db.conn.execute(
        "SELECT item_id, text_hash, vec FROM item_embeddings WHERE model=?", (embedder.model_id,))}
    vecs = {i: from_blob(have[i][1]) for i in texts if i in have and have[i][0] == hashes[i]}
    todo = [i for i in texts if i not in vecs]
    for start in range(0, len(todo), cfg.batch_size):
        chunk = todo[start:start + cfg.batch_size]
        for i, v in zip(chunk, embedder.embed_docs([texts[i] for i in chunk]), strict=True):
            vecs[i] = v
    with db.conn:
        db.conn.executemany(
            "INSERT OR REPLACE INTO item_embeddings(item_id, model, dim, vec, text_hash, created_at) VALUES (?,?,?,?,?,?)",
            [(i, embedder.model_id, len(vecs[i]), to_blob(vecs[i]), hashes[i], now_kst()) for i in todo])
    return vecs, len(todo)


def run_filter(db: DB, cfg: FilterConfig, embedder: Embedder, run_id: str, since: date | None = None,
               until: date | None = None, origin_rank: dict[str, int] | None = None) -> FilterResult:
    """기간의 글·영상 전부(키워드 판정과 무관)를 점수 매겨 item_relevance에 저장하고, 같은 URL을 연결한다."""
    from .dedupe import link_same_urls

    t0 = time.monotonic()
    res = FilterResult(run_id, embedder.model_id, embedder.device)
    rows = item_rows(db, since, until)
    queries = embedder.embed_queries([x.text for x in cfg.interests])
    interests = [(x.keyword_id, q) for x, q in zip(cfg.interests, queries, strict=True)]
    vecs, res.computed = embeddings_for(db, embedder, rows, cfg)
    out = []
    for r in rows:
        score, kid = best_interest(vecs[r["id"]], interests)
        decision, reason = decide(r["filter_status"], r["filter_reason"], score, cfg)
        res.decisions[reason] = res.decisions.get(reason, 0) + 1
        out.append((r["id"], embedder.model_id, score, kid, decision, reason, run_id))
        res.rows.append({"id": r["id"], "source": r["source_id"], "channel": r["channel"], "title": r["title"],
                         "keyword_status": r["filter_status"], "keyword_reason": r["filter_reason"] or "",
                         "score": score, "keyword_id": kid, "decision": decision, "reason": reason})
    with db.conn:
        db.conn.executemany(
            "INSERT OR REPLACE INTO item_relevance(item_id, model, score, keyword_id, decision, reason, run_id) "
            "VALUES (?,?,?,?,?,?,?)", out)
    res.n = len(rows)
    res.same_as = link_same_urls(db, [r["id"] for r in rows if r["channel"] == "text"], cfg, origin_rank or {})
    res.seconds = time.monotonic() - t0
    return res


def similar_pairs(db: DB, model: str, item_ids: list[int], k: int) -> list[tuple[float, int, int]]:
    """내용이 비슷한 다른 글 쌍 상위 k(같은 URL로 연결된 쌍 제외). 지우거나 합치지 않고 리포트에만(S5 묶기 재료)."""
    if k <= 0 or len(item_ids) < 2:
        return []
    marks = ",".join("?" * len(item_ids))
    vecs = {r["item_id"]: from_blob(r["vec"]) for r in db.conn.execute(
        f"SELECT item_id, vec FROM item_embeddings WHERE model=? AND item_id IN ({marks})", (model, *item_ids))}
    canon = {r["item_id"]: r["canonical_id"] for r in db.conn.execute("SELECT item_id, canonical_id FROM item_same_as")}
    ids = sorted(vecs)
    pairs = []
    for a_i, a in enumerate(ids):
        for b in ids[a_i + 1:]:
            if canon.get(a, a) == canon.get(b, b):
                continue
            pairs.append((round(cosine(vecs[a], vecs[b]), 4), a, b))
    return sorted(pairs, reverse=True)[:k]
