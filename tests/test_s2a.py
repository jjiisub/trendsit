"""S2 2a: 키워드 재판정(A5), 임베딩 필터(A6), URL 중복 연결(A7), filter.yaml 검증(A3). 네트워크·모델 없이(모의 임베더)."""

import shutil
from datetime import date

import pytest
import yaml

from tests.test_config import edit_yaml
from trendsit.core import config
from trendsit.core.config import ROOT, FilterConfig, KeywordsConfig
from trendsit.core.db import DB
from trendsit.filter.dedupe import link_same_urls
from trendsit.filter.embed import HashEmbedder, cosine, decide, from_blob, run_filter, to_blob
from trendsit.filter.rematch import rematch
from trendsit.filter.report import distribution, make_relevance_labels, seed_results

KW = KeywordsConfig.model_validate({"keywords": [
    {"id": "agent", "canonical": "에이전트", "aliases": ["agent", "에이전트"]},
    {"id": "rag-search", "canonical": "RAG", "aliases": ["RAG", "임베딩"]},
], "exclude": ["주가"]})


def cfg(**kw) -> FilterConfig:
    base = {"model": "mock", "instruction": "판단", "drop_below": 0.3, "rescue_above": 0.5,
            "interests": [{"keyword_id": "agent", "text": "AI 에이전트 도구 호출 계획 실행 agent tool"},
                          {"keyword_id": "rag-search", "text": "RAG 검색 임베딩 벡터 데이터베이스 retrieval"}],
            "source_kind": {"simonw": "blog"}}
    return FilterConfig.model_validate(base | kw)


def add_item(db, iid, source, title, body="", *, url=None, channel="text", status="pass", reason=None,
             day="2026-10-01", origin=None, published=None):
    db.conn.execute(
        "INSERT INTO items(id, source_id, channel, kind, external_id, url, title, day, week, summary_feed, "
        "filter_status, filter_reason, score, published_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (iid, source, channel, "x", f"e{iid}", url or f"https://{source}.example/{iid}", title, day, "2026-W40", None,
         status, reason, 0, published or f"{day}T09:00:00+09:00"))
    db.conn.execute("INSERT INTO item_texts(item_id, text) VALUES (?, ?)", (iid, body))
    if origin:
        db.conn.execute("INSERT INTO links(item_id, url, role) VALUES (?, ?, 'origin_candidate')", (iid, origin))
    db.conn.commit()


@pytest.fixture
def db(tmp_path):
    d = DB(tmp_path / "t.db")
    for sid, kind in (("openai", "primary"), ("simonw", "curation"), ("aitimes", "news"), ("geeknews", "curation")):
        d.conn.execute("INSERT INTO sources(id, channel, kind, name) VALUES (?, 'text', ?, ?)", (sid, kind, sid))
    d.conn.commit()
    return d


# ---------- A5 rematch ----------
def test_rematch_updates_status_and_keywords_and_is_idempotent(db):
    add_item(db, 1, "openai", "새 agent 프레임워크", status="filtered", reason="no_keyword")
    add_item(db, 2, "aitimes", "RAG 실전", "임베딩 모델 비교")
    add_item(db, 3, "aitimes", "agent 회사 주가 급등", status="pass")
    db.conn.execute("INSERT INTO item_keywords VALUES (2, 'old-kw', 'title')")
    db.conn.commit()
    res = rematch(db, KW)
    rows = {r["id"]: r for r in db.conn.execute("SELECT * FROM items")}
    assert rows[1]["filter_status"] == "pass" and rows[1]["score"] == 3
    kws = {(r["item_id"], r["keyword_id"]) for r in db.conn.execute("SELECT * FROM item_keywords")}
    assert (2, "rag-search") in kws and (2, "old-kw") not in kws
    assert rows[3]["filter_status"] == "pass"  # 제목에 포함 키워드가 있으면 제외어가 있어도 통과(S1 규칙 그대로)
    assert res.items == 3 and res.status_changed == {"filtered→pass": 1}
    again = rematch(db, KW)
    assert again.items_changed == 0 and again.repos_changed == 0


def test_rematch_period_and_trending(db):
    add_item(db, 1, "openai", "agent 소식", day="2026-09-01", status="filtered", reason="no_keyword")
    db.conn.execute("INSERT INTO repos(full_name, description, readme_head) VALUES ('a/b', 'RAG toolkit', 'agent')")
    db.conn.execute("INSERT INTO repo_trending(week, full_name, score, filter_status, filter_reason, keywords) "
                    "VALUES ('2026-W40', 'a/b', 0, 'filtered', 'no_keyword', '{}')")
    db.conn.commit()
    res = rematch(db, KW, date(2026, 10, 1), date(2026, 10, 7))
    assert res.items == 0  # 기간 밖 항목은 그대로
    assert res.repos == 0  # 기간 주차(항목 없음)의 트렌딩만
    res = rematch(db, KW)
    row = db.conn.execute("SELECT * FROM repo_trending").fetchone()
    assert res.repos_changed == 1 and row["filter_status"] == "pass" and '"rag-search"' in row["keywords"]


def test_real_keywords_file_is_the_handoff_draft():
    real = yaml.safe_load((ROOT / "config/keywords.yaml").read_text(encoding="utf-8"))
    draft = yaml.safe_load((ROOT / "docs/handoff/keywords_next.yaml").read_text(encoding="utf-8"))
    assert real == draft and len(real["keywords"]) == 13


# ---------- A6 filter ----------
@pytest.mark.parametrize("status,reason,score,expect", [
    ("pass", None, 0.35, ("keep", "keyword_pass")),
    ("pass", None, 0.10, ("drop", "low_similarity")),
    ("filtered", "no_keyword", 0.60, ("keep", "rescued")),
    ("filtered", "no_keyword", 0.40, ("drop", "no_keyword")),
    ("filtered", "excluded:주가", 0.99, ("drop", "excluded:주가")),
])
def test_four_way_decision(status, reason, score, expect):
    assert decide(status, reason, score, cfg()) == expect


def test_run_filter_scores_stores_and_reuses_embeddings(db):
    add_item(db, 1, "openai", "AI 에이전트 도구 호출", "agent tool 계획 실행")  # 통과 + 높음
    add_item(db, 2, "aitimes", "agent 회사 행사 안내", "행사 일정 장소 참가")  # 통과 + 낮음
    add_item(db, 3, "aitimes", "벡터 데이터베이스 비교", "RAG 검색 임베딩 retrieval", status="filtered", reason="no_keyword")
    add_item(db, 4, "aitimes", "RAG 임베딩 주가", "RAG 검색 임베딩 retrieval", status="filtered", reason="excluded:주가")
    add_item(db, 5, "openai", "영상", "에이전트 데모", channel="video")
    e = HashEmbedder()
    c = cfg(drop_below=0.3, rescue_above=0.4)
    res = run_filter(db, c, e, "run1")
    got = {r["item_id"]: (r["decision"], r["reason"]) for r in db.conn.execute("SELECT * FROM item_relevance")}
    assert got[1] == ("keep", "keyword_pass")
    assert got[2] == ("drop", "low_similarity")
    assert got[3] == ("keep", "rescued")
    assert got[4] == ("drop", "excluded:주가")  # 점수가 높아도 되살리지 않음
    assert 5 in got  # 영상도 대상
    assert res.computed == 5
    # S1 키워드 판정은 그대로
    assert db.conn.execute("SELECT filter_status FROM items WHERE id=3").fetchone()[0] == "filtered"
    # 두 번째 실행: 임베딩 계산 0
    again = run_filter(db, c, e, "run2")
    assert again.computed == 0 and again.decisions == res.decisions
    # 입력이 바뀌면 그 항목만 다시
    db.conn.execute("UPDATE items SET title='바뀐 제목' WHERE id=2")
    db.conn.commit()
    assert run_filter(db, c, e, "run3").computed == 1


def test_blob_roundtrip_and_cosine():
    e = HashEmbedder()
    v = e.embed_docs(["에이전트 도구"])[0]
    assert abs(cosine(v, v) - 1) < 1e-6
    assert from_blob(to_blob(v)) == pytest.approx(v, abs=1e-6)


def test_distribution_and_labels(tmp_path):
    rows = [{"id": i, "source": "s", "channel": "text", "title": f"t{i}", "keyword_status": "pass" if i % 2 else "filtered",
             "keyword_reason": "" if i % 2 else "no_keyword", "score": i / 100, "decision": "keep", "reason": "x"}
            for i in range(60)]
    dist = distribution(rows)
    assert sum(p + q for _, p, q in dist) == 60
    path = tmp_path / "relevance.csv"
    assert make_relevance_labels(rows, path) == 40
    text = path.read_text(encoding="utf-8").replace(",keep,\n", ",keep,keep\n", 1)  # 사용자가 하나 채움
    path.write_text(text, encoding="utf-8")
    make_relevance_labels(rows, path)
    assert ",keep,keep" in path.read_text(encoding="utf-8")  # 채운 라벨 보존


def test_seed_lookup_by_source_and_title_prefix(tmp_path):
    seed = tmp_path / "seed.csv"
    seed.write_text("source,title,expected,why\nanthropic,Anthropic invests $100 million to train,keep,x\n"
                    "openai,없는 글,drop,x\n", encoding="utf-8")
    rows = [{"id": 1, "source": "anthropic", "title": "Anthropic invests $100 million to train 10,000 engineers",
             "score": 0.5, "decision": "keep"}]
    res = seed_results(rows, seed)
    assert res[0]["correct"] is True and res[1]["found"] is False


# ---------- A7 dedupe ----------
def test_same_url_links_to_most_original(db):
    blog = "https://simonwillison.net/2026/Oct/1/post/"
    add_item(db, 1, "geeknews", "GN 소개", url="https://news.hada.io/topic?id=1", origin=blog + "?utm_source=gn")
    add_item(db, 2, "simonw", "원글", url=blog)
    add_item(db, 3, "aitimes", "기사", url="https://aitimes.example/a", origin="https://simonwillison.net/2026/Oct/1/post")
    add_item(db, 4, "aitimes", "다른 글")
    n = link_same_urls(db, [1, 2, 3, 4], cfg())
    rows = {r["item_id"]: r for r in db.conn.execute("SELECT * FROM item_same_as")}
    assert n == 2 and set(rows) == {1, 3}
    assert rows[1]["canonical_id"] == 2 and rows[3]["canonical_id"] == 2  # 개인 블로그(simonw: blog)가 기준
    assert rows[1]["reason"] == "same_url:https://simonwillison.net/2026/Oct/1/post"
    # 공식 소스가 같은 URL이면 공식이 기준
    add_item(db, 5, "openai", "공식 글", url=blog)
    link_same_urls(db, [1, 2, 3, 4, 5], cfg())
    assert {r["canonical_id"] for r in db.conn.execute("SELECT * FROM item_same_as")} == {5}
    # 다시 돌려도 같음
    assert link_same_urls(db, [1, 2, 3, 4, 5], cfg()) == 3


# ---------- A3 filter.yaml ----------
def copy_config(tmp_path):
    root = tmp_path / "root"
    shutil.copytree(ROOT / "config", root / "config")
    return root


def test_filter_yaml_passes_and_bad_values_point_to_path(tmp_path):
    assert config.check_all() == []
    root = copy_config(tmp_path)
    edit_yaml(root / "config/filter.yaml", lambda d: d["interests"][2].__setitem__("keyword_id", "no-such"))
    errs = config.check_all(root / "config")
    assert [(e.file, e.path) for e in errs] == [("filter.yaml", "interests[2].keyword_id")]
    root = copy_config(tmp_path / "b")
    edit_yaml(root / "config/filter.yaml", lambda d: d.__setitem__("drop_below", 1.5))
    errs = config.check_all(root / "config")
    assert [(e.file, e.path) for e in errs] == [("filter.yaml", "drop_below")]
    root = copy_config(tmp_path / "c")
    edit_yaml(root / "config/filter.yaml", lambda d: d.__setitem__("rescue_above", 0.1))
    assert "rescue_above" in config.check_all(root / "config")[0].reason


# ---------- 실제 임베딩 모델(embed 묶음이 있을 때만. 이 한 종류만 건너뜀 허용, S2S3_TASK 2장) ----------
def test_real_embedder_scores_fixtures_in_range():
    pytest.importorskip("sentence_transformers", reason="embed 선택 묶음 없음(uv sync --extra embed)")
    from trendsit.cli_text import load_filter_fixtures
    from trendsit.filter.embed import SentenceEmbedder, best_interest

    c = config.load("filter.yaml")
    # 장치는 운영과 같이 자동(맥 MPS, 리눅스 CPU). 맥 CPU는 bf16 가중치를 하드웨어 지원 없이 계산해 1시간 넘게 걸림(S2 리포트)
    e = SentenceEmbedder(c.model, c.instruction)
    interests = list(zip([x.keyword_id for x in c.interests], e.embed_queries([x.text for x in c.interests]),
                         strict=True))
    fx = load_filter_fixtures()
    scores = [best_interest(v, interests)[0] for v in e.embed_docs([f["input"]["text"] for _, f in fx])]
    assert len(scores) == 20 and all(-1 <= s <= 1 for s in scores)
