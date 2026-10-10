"""S5 0단계: 유튜브 RSS가 실패하면 채널 목록(yt-dlp)으로 대체."""

import json
from datetime import date

from tests.test_s1b import FIX, FixtureTransport, fake_ytdlp, fetcher_for
from trendsit.collect.run import collect
from trendsit.core import config
from trendsit.core.db import DB


def _feed() -> str:
    return next(v.feed for v in config.load("sources.yaml").video if v.id == "techbridge")


def test_rss_404_falls_back_to_channel_listing(tmp_path):
    meta = json.loads((FIX / "bf_youtube" / "meta.json").read_text())
    tr = FixtureTransport("bf_youtube", override={_feed(): 404})
    res = collect(date.fromisoformat(meta["since"]), date.fromisoformat(meta["until"]), only="techbridge",
                  data_dir=tmp_path, fetcher=fetcher_for(tr), ytdlp=fake_ytdlp("bf_youtube"),
                  today=date.fromisoformat(meta["today"]))
    d = res.sources["techbridge"]
    # 녹화에 없는 영상은 메타데이터가 비어 partial이 될 수 있다(대략 날짜로 저장)
    assert d["status"] in ("ok", "partial") and "techbridge" not in res.failed
    assert any("채널 목록으로 대체" in n for n in d["notes"])
    assert d["n_new"] >= 1 and d["n_new"] == d["n_backfilled"]
    db = DB(tmp_path / "trendsit.db")
    days = [r[0] for r in db.conn.execute("SELECT day FROM items WHERE source_id='techbridge'")]
    assert days and all(meta["since"] <= x <= meta["until"] for x in days)


def test_rss_404_and_listing_failure_is_source_failure(tmp_path):
    meta = json.loads((FIX / "bf_youtube" / "meta.json").read_text())
    tr = FixtureTransport("bf_youtube", override={_feed(): 404})
    res = collect(date.fromisoformat(meta["since"]), date.fromisoformat(meta["until"]), only="techbridge",
                  data_dir=tmp_path, fetcher=fetcher_for(tr), ytdlp=lambda args: None,
                  today=date.fromisoformat(meta["today"]))
    assert res.failed == ["techbridge"]
    assert "채널 목록도 실패" in res.sources["techbridge"]["error"]
