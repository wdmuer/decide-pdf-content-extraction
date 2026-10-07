import functools
import http.server
import os
import threading
import time

import langdetect
import pytest
import requests
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from .tasks import FIXTURES

ENDPOINT = os.environ["MU_SPARQL_ENDPOINT"]
TIKA_URL = os.environ["APACHE_TIKA_URL"]

LLM_MODULES = ("src.LLMAnalyzer",)

SITE_PORT = 8000

# langdetect is random on every call unless seeded.
langdetect.DetectorFactory.seed = 0


def _wait_until_up(probe):
    deadline = time.monotonic() + 180
    while True:
        try:
            probe().raise_for_status()
            return
        except requests.RequestException:
            if time.monotonic() > deadline:
                raise
            time.sleep(2)


@pytest.fixture(scope="session", autouse=True)
def virtuoso():
    _wait_until_up(lambda: requests.post(ENDPOINT, data={"query": "ASK { ?s ?p ?o }"}, timeout=10))


@pytest.fixture(scope="session", autouse=True)
def tika():
    _wait_until_up(lambda: requests.get(TIKA_URL, timeout=10))


@pytest.fixture(scope="session")
def pdf_site():
    """Serve the fixtures directory on 127.0.0.1:8000, where the task downloads the PDFs from."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=FIXTURES)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", SITE_PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield
    server.shutdown()


@pytest.fixture
def stub_llm(monkeypatch):
    """Make every init_chat_model call return a model that answers ``response``."""
    def install(response: str) -> None:
        for module in LLM_MODULES:
            monkeypatch.setattr(
                f"{module}.init_chat_model",
                lambda *args, **kwargs: FakeListChatModel(responses=[response]),
            )
    return install
