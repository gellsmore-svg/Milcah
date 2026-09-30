import json
from email.message import Message
import pytest
from milcah.web_research import (
    WebResearchClient,
    WebResearchConfig,
    _PinnedHTTPConnection,
    _public_url,
)


def test_user_agent_names_milcah():
    assert WebResearchConfig().user_agent == "Milcah-WebResearch/0.2"


@pytest.mark.parametrize("address", ["224.0.0.1", "100.64.0.1", "64:ff9b::7f00:1", "10.1.1.1"])
def test_non_public_addresses_are_blocked(monkeypatch, address):
    monkeypatch.setattr(
        "milcah.web_research.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", (address, 80))],
    )
    with pytest.raises(ValueError, match="Private or non-global"):
        _public_url("http://example.test/x", allow_private_hosts=False)


def test_connection_uses_the_checked_address(monkeypatch):
    monkeypatch.setattr(
        "milcah.web_research.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 80))],
    )
    seen = {}

    def fake_create(address, timeout, source_address):
        seen["address"] = address
        raise OSError("stop")

    conn = _PinnedHTTPConnection("example.test", 80, timeout=1, allow_private_hosts=False)
    monkeypatch.setattr(conn, "_create_connection", fake_create)
    with pytest.raises(OSError, match="stop"):
        conn.connect()
    assert seen["address"] == ("93.184.216.34", 80)


def test_private_hosts_blocked(monkeypatch):
    monkeypatch.setattr(
        "milcah.web_research.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("10.0.0.2", 80))],
    )
    with pytest.raises(ValueError, match="Private"):
        _public_url("http://internal.test", allow_private_hosts=False)


def test_research_searches_and_fetches(monkeypatch):
    monkeypatch.setattr(
        "milcah.web_research.socket.getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )

    class Response:
        def __init__(self, body, content_type="application/json"):
            self.body = body
            self.headers = Message()
            self.headers["Content-Type"] = content_type

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self, n=-1):
            return self.body[:n]

    client = WebResearchClient(
        WebResearchConfig(enabled=True, allow_private_search_endpoint=True, max_pages=1)
    )
    responses = iter(
        [
            Response(
                json.dumps(
                    {
                        "results": [
                            {
                                "title": "T",
                                "url": "https://example.test",
                                "content": "S",
                            }
                        ]
                    }
                ).encode()
            ),
            Response(b"<p>Evidence</p>", "text/html"),
        ]
    )
    monkeypatch.setattr(client, "_open", lambda url, **kwargs: next(responses))
    sources = client.research("query")
    assert sources[0].snippet == "S" and sources[0].content == "Evidence"
