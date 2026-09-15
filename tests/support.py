"""Fixture transport and isolated filesystem for offline unit tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ORIGINAL_URL = "https://news.example.test/articles/synthetic"
TSTAMP = "20200101000000"


class FixtureResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def json(self) -> dict:
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        return None


class FixtureSession:
    """Consume explicit responses; unexpected requests fail without any network."""

    def __init__(self, *responses: tuple[str, bytes]) -> None:
        self.responses = deque(responses)
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs) -> FixtureResponse:
        if not self.responses:
            raise AssertionError(f"Unexpected fixture request: {url}")
        expected_url, content = self.responses.popleft()
        if url != expected_url:
            raise AssertionError(f"Expected {expected_url}, got {url}")
        self.calls.append((url, kwargs))
        return FixtureResponse(content)


class OfflineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        # Fail immediately if a test accidentally bypasses the fixture transport.
        for target in (
            "requests.sessions.Session.request",
            "socket.create_connection",
            "socket.socket.connect",
            "socket.socket.connect_ex",
        ):
            self.enterContext(
                patch(target, side_effect=AssertionError("Network forbidden in unit tests"))
            )
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def fixture_session(self, *responses: tuple[str, bytes]) -> FixtureSession:
        session = FixtureSession(*responses)
        self.addCleanup(self.assertEqual, session.responses, deque())
        return session
