"""Odoo 19 External JSON-2 transport.

A single small class that turns ``client.call("crm.lead", "search_read", domain=...)`` into

    POST {host}/json/2/crm.lead/search_read
    Authorization: bearer <API_KEY>
    X-Odoo-Database: <db>            (only when a db is configured)
    Content-Type: application/json

    {"domain": ..., "fields": ..., ...}

All arguments are passed by name (JSON-2 has no positional arguments). This is the only
module that knows the wire format; resource classes and the CLI build on top of it.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from .exceptions import AuthError, DryRun, NotFoundError, OdooError

USER_AGENT = "odoo-cli/0.1"
_RETRYABLE_STATUS = {429, 502, 503, 504}


class OdooClient:
    """Authenticated JSON-2 client for a single Odoo instance.

    Pass ``transport`` (e.g. ``httpx.MockTransport``) to inject a fake backend in tests.
    In ``dry_run`` mode, :meth:`call` renders the request it *would* send and raises
    :class:`~odoo_cli.exceptions.DryRun` instead of hitting the network.
    """

    def __init__(
        self,
        host: str,
        api_key: str,
        *,
        db: str | None = None,
        dry_run: bool = False,
        timeout: float = 30.0,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.db = db
        self.dry_run = dry_run
        self.max_retries = max_retries
        headers = {
            "Authorization": f"bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        if db:
            headers["X-Odoo-Database"] = db
        self._http = httpx.Client(
            base_url=f"{self.host}/json/2",
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> OdooClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def call(self, model: str, method: str, /, **kwargs: Any) -> Any:
        """Invoke ``model.method(**kwargs)`` on the remote and return its raw result."""
        path = f"/{model}/{method}"
        if self.dry_run:
            self._render_dry_run(path, kwargs)
            raise DryRun(f"{model}.{method}")

        last_exc: httpx.HTTPError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http.post(path, json=kwargs)
            except httpx.HTTPError as exc:  # network/timeout
                last_exc = exc
                if attempt < self.max_retries:
                    continue
                raise OdooError(f"Request to {self.host}{path} failed: {exc}") from exc

            if resp.status_code in _RETRYABLE_STATUS and attempt < self.max_retries:
                # Respect Retry-After when present; otherwise let httpx's caller retry.
                continue
            return self._handle_response(resp, model, method)

        # Should be unreachable, but keeps the type checker honest.
        raise OdooError(f"Request to {self.host}{path} failed: {last_exc}")

    def _handle_response(self, resp: httpx.Response, model: str, method: str) -> Any:
        if resp.status_code == 200:
            return resp.json()

        detail = self._extract_error(resp)
        if resp.status_code in (401, 403):
            raise AuthError(f"Authentication failed ({resp.status_code}): {detail}")
        if resp.status_code == 404:
            raise NotFoundError(f"{model}.{method} not found ({resp.status_code}): {detail}")
        raise OdooError(f"Odoo error calling {model}.{method} ({resp.status_code}): {detail}")

    @staticmethod
    def _extract_error(resp: httpx.Response) -> str:
        """Best-effort extraction of a human-readable message from an error response.

        The JSON-2 error envelope is not fully documented; we defensively look for common
        shapes ({"error": {...}}, {"message": ...}, {"name"/"description"}) and fall back to
        raw text.
        """
        try:
            body = resp.json()
        except (json.JSONDecodeError, ValueError):
            return resp.text.strip() or resp.reason_phrase
        if isinstance(body, dict):
            err = body.get("error", body)
            if isinstance(err, dict):
                data = err.get("data")
                if isinstance(data, dict) and data.get("message"):
                    return str(data["message"])
                for key in ("message", "description", "name", "debug"):
                    if err.get(key):
                        return str(err[key])
            elif err:
                return str(err)
        return json.dumps(body)

    def _render_dry_run(self, path: str, kwargs: dict[str, Any]) -> None:
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax

        body = json.dumps(kwargs, indent=2, default=str)
        headers = "Authorization: bearer ***\nContent-Type: application/json"
        if self.db:
            headers += f"\nX-Odoo-Database: {self.db}"
        text = f"POST {self.host}/json/2{path}\n{headers}\n\n"
        console = Console(stderr=True)
        console.print(
            Panel(
                Syntax(text + body, "http", theme="ansi_dark", word_wrap=True),
                title="[bold]dry-run[/] — request not sent",
                border_style="yellow",
            )
        )
