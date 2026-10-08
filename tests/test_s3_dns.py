"""M3: safe_fetch 연결 주소 고정(DNS 재바인딩). 검사한 IP로만 연결하고, Host는 원래 이름. 리다이렉트마다 다시 풀고 고정."""

import httpcore
import pytest

from trendsit.collect.fetch import Fetcher, PinnedBackend

A, B, C = "93.184.216.34", "127.0.0.1", "151.101.1.69"


class Recorder(httpcore.MockBackend):
    """연결 주소를 기록하고 미리 정한 HTTP 응답을 돌려주는 가짜 네트워크."""

    def __init__(self, responses: list[bytes]):
        super().__init__(buffer=[])
        self.responses = responses
        self.hosts: list[str] = []
        self.sent: list[bytes] = []

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        self.hosts.append(host)
        rec = self

        class Stream(httpcore.MockStream):
            def write(self, buffer, timeout=None):
                rec.sent.append(buffer)

        return Stream([rec.responses.pop(0)])


def ok(body=b"hello", extra=b""):
    return (b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: " + str(len(body)).encode()
            + b"\r\nConnection: close\r\n" + extra + b"\r\n" + body)


def test_connection_uses_checked_ip_not_later_dns(monkeypatch):
    # 연결할 때 이름을 다시 풀면 루프백이 나오는 재바인딩 상황: 운영체제 리졸버는 아예 쓰이지 않아야 한다
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, 1, 6, "", (B, 80))])
    rec = Recorder([ok()])
    f = Fetcher(None, use_cache=False, resolver=lambda h: [A], network_backend=rec, sleep=lambda s: None)
    res = f.fetch("http://rebind.example/x", kind="api")
    assert res.ok and res.text == "hello"
    assert rec.hosts == [A]  # 연결은 검사한 IP로
    assert b"Host: rebind.example" in rec.sent[0]  # Host 헤더는 원래 이름
    assert f.backend.connected == [("rebind.example", A, 80)]


def test_second_check_with_rebound_answer_is_blocked():
    answers = iter([[A], [B]])  # 검사 사이에 답이 바뀌면 두 번째 검사에서 막힘
    rec = Recorder([ok()])
    f = Fetcher(None, use_cache=False, resolver=lambda h: next(answers), network_backend=rec, sleep=lambda s: None)
    res = f.fetch("http://rebind.example/x", kind="api")
    assert not res.ok and "공인 주소가 아님" in res.error and rec.hosts == []


def test_redirect_resolves_and_pins_again():
    rec = Recorder([b"HTTP/1.1 302 Found\r\nLocation: http://second.example/y\r\nContent-Length: 0\r\n"
                    b"Connection: close\r\n\r\n", ok(b"done")])
    table = {"first.example": [A], "second.example": [C]}
    f = Fetcher(None, use_cache=False, resolver=lambda h: table[h], network_backend=rec, sleep=lambda s: None)
    res = f.fetch("http://first.example/x", kind="api")
    assert res.ok and res.final_url == "http://second.example/y"
    assert rec.hosts == [A, C]


def test_redirect_to_private_is_blocked_before_connect():
    rec = Recorder([b"HTTP/1.1 302 Found\r\nLocation: http://evil.example/\r\nContent-Length: 0\r\n"
                    b"Connection: close\r\n\r\n"])
    table = {"first.example": [A], "evil.example": [B]}
    f = Fetcher(None, use_cache=False, resolver=lambda h: table[h], network_backend=rec, sleep=lambda s: None)
    res = f.fetch("http://first.example/x", kind="api")
    assert not res.ok and "공인 주소가 아님" in res.error
    assert rec.hosts == [A]  # 사설 주소로는 연결하지 않음


def test_backend_refuses_unchecked_hostname():
    backend = PinnedBackend({}, Recorder([ok()]))
    with pytest.raises(httpcore.ConnectError):
        backend.connect_tcp("never-checked.example", 443)
    backend.connect_tcp(A, 443)  # IP 리터럴은 검사(_check_url)를 거친 것이라 그대로
