"""비밀 안전: HTTP 녹화 파일에 Authorization 헤더·토큰이 남지 않음, 녹화 저장 전 비밀 지우기, 다른 호스트 리다이렉트에 토큰 안 넘김."""

import gzip
import json
import re
from pathlib import Path

import httpx

from trendsit.collect.fetch import Fetcher
from trendsit.core import config

FIX = Path(__file__).parent / "fixtures" / "http"
# 헤더 형태(Authorization: …, "authorization": …)와 토큰 형태. 본문 산문 속 'authorization' 단어는 대상이 아니다
HEADER = re.compile(rb'(?im)^\s*authorization\s*:|"authorization"\s*:')
TOKEN = re.compile(rb"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}"
                   rb"|(?i:bearer|token)\s+[A-Za-z0-9_\-]{30,}")
INDEX_KEYS = {"file", "status", "content_type", "location", "recorded", "synthetic"}


def bodies():
    for f in sorted(FIX.rglob("*")):
        if f.is_file():
            b = f.read_bytes()
            yield f, gzip.decompress(b) if f.suffix == ".gz" else b


def test_recordings_have_no_authorization_header_or_token():
    secrets = [v.encode() for n in config.SECRET_NAMES if (v := config.get_secret(n)) and len(v) >= 8]
    bad = []
    for f, b in bodies():
        if HEADER.search(b) or TOKEN.search(b) or any(s in b for s in secrets):
            bad.append(str(f.relative_to(FIX)))
    assert not bad, f"녹화에 헤더·토큰 형태 문자열: {bad}"


def test_recording_index_stores_no_request_headers():
    for idx in FIX.glob("*/index.json"):
        for url, meta in json.loads(idx.read_text()).items():
            assert set(meta) <= INDEX_KEYS, f"{idx.parent.name} {url}: {set(meta) - INDEX_KEYS}"


def test_redact_secrets(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SECRET_FILE", tmp_path / "none.env")
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_SECRETVALUE123456")
    out = config.redact_secrets(b'{"echo": "github_pat_SECRETVALUE123456", "ok": 1}')
    assert out == b'{"echo": "[REDACTED]", "ok": 1}'


class Redirector(httpx.BaseTransport):
    def __init__(self, target: str):
        self.target, self.seen = target, []

    def handle_request(self, request):
        self.seen.append((str(request.url), request.headers.get("authorization")))
        if len(self.seen) == 1:
            return httpx.Response(302, headers={"location": self.target}, request=request)
        return httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}", request=request)


def test_authorization_dropped_on_cross_host_redirect():
    for target, kept in (("https://api.github.com/repositories/1", True), ("https://evil.example.com/x", False)):
        t = Redirector(target)
        f = Fetcher(None, use_cache=False, transport=t, resolver=lambda host: ["140.82.112.6"], sleep=lambda s: None)
        f.fetch("https://api.github.com/repos/a/b", kind="api", headers={"Authorization": "Bearer x"})
        assert t.seen[0][1] == "Bearer x"
        assert (t.seen[1][1] == "Bearer x") is kept
