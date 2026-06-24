import json
from email.message import Message
import pytest
from milcah.web_research import WebResearchClient, WebResearchConfig, _public_url


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
