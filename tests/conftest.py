"""Shared test fixtures: a mock JSON-2 backend wired into OdooClient."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from odoo_cli.client import OdooClient

# A handler maps (model, method, body) -> the JSON value Odoo would return.
Handler = Callable[[str, str, dict[str, Any]], Any]


class MockBackend:
    """Records requests and dispatches to a per-(model, method) handler."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self._routes: dict[tuple[str, str], Handler] = {}
        self._status: dict[tuple[str, str], int] = {}

    def route(self, model: str, method: str, handler: Handler) -> None:
        self._routes[(model, method)] = handler

    def fail(self, model: str, method: str, status: int, body: Any) -> None:
        self._status[(model, method)] = status
        self._routes[(model, method)] = lambda *_: body

    def transport(self) -> httpx.MockTransport:
        def respond(request: httpx.Request) -> httpx.Response:
            # base_url is .../json/2 ; path is /<model>/<method>
            _, model, method = request.url.path.rsplit("/", 2)
            body = json.loads(request.content or b"{}")
            self.requests.append(
                {"model": model, "method": method, "body": body, "headers": request.headers}
            )
            key = (model, method)
            status = self._status.get(key, 200)
            handler = self._routes.get(key)
            payload = handler(model, method, body) if handler else None
            return httpx.Response(status, json=payload)

        return httpx.MockTransport(respond)


@pytest.fixture
def backend() -> MockBackend:
    return MockBackend()


@pytest.fixture
def client(backend: MockBackend) -> OdooClient:
    return OdooClient(
        "https://demo.example.com",
        "test-key",
        db="demo",
        transport=backend.transport(),
    )
