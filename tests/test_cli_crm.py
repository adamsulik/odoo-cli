"""End-to-end CLI tests via Typer's CliRunner, backed by the mock JSON-2 transport."""

from __future__ import annotations

import functools
import json

import pytest
from typer.testing import CliRunner

from odoo_cli.cli import main
from odoo_cli.client import OdooClient

runner = CliRunner()


@pytest.fixture(autouse=True)
def env(monkeypatch):
    """Make config.resolve succeed from env vars (no config file / keyring needed)."""
    monkeypatch.setenv("ODOO_URL", "https://demo.example.com")
    monkeypatch.setenv("ODOO_API_KEY", "test-key")
    monkeypatch.delenv("ODOO_DB", raising=False)
    monkeypatch.delenv("ODOO_PROFILE", raising=False)


@pytest.fixture
def wire(backend, monkeypatch):
    """Route the CLI's OdooClient through the mock backend transport."""
    factory = functools.partial(OdooClient, transport=backend.transport())
    monkeypatch.setattr(main, "OdooClient", factory)
    return backend


def test_leads_list_json(wire):
    wire.route(
        "crm.lead",
        "search_read",
        lambda *_: [{"id": 1, "name": "Big deal", "user_id": [3, "Jane"]}],
    )
    result = runner.invoke(main.app, ["--json", "crm", "leads", "list", "--limit", "5"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data[0]["name"] == "Big deal"
    assert wire.requests[-1]["body"]["limit"] == 5


def test_leads_create_resolves_user_and_writes(wire):
    wire.route("res.users", "search_read", lambda *_: [{"id": 3, "name": "Jane", "login": "jane"}])
    wire.route("crm.lead", "create", lambda *_: 99)
    wire.route("crm.lead", "read", lambda *_: [{"id": 99, "name": "New", "user_id": [3, "Jane"]}])

    result = runner.invoke(
        main.app, ["--json", "crm", "leads", "create", "--name", "New", "--user", "Jane"]
    )
    assert result.exit_code == 0, result.output
    create_req = next(r for r in wire.requests if r["method"] == "create")
    assert create_req["body"]["vals"]["user_id"] == 3


def test_leads_assign_ambiguous_user_errors(wire):
    wire.route(
        "res.users",
        "search_read",
        lambda *_: [
            {"id": 1, "name": "Jan A", "login": "jana"},
            {"id": 2, "name": "Jan B", "login": "janb"},
        ],
    )
    result = runner.invoke(main.app, ["crm", "leads", "assign", "5", "--user", "Jan"])
    assert result.exit_code == 1
    assert "matches 2 users" in result.output


def test_dry_run_does_not_send(wire):
    result = runner.invoke(main.app, ["--dry-run", "crm", "leads", "create", "--name", "X"])
    assert result.exit_code == 0, result.output
    assert wire.requests == []


def test_leads_messages_strips_html_in_table(wire):
    wire.route(
        "mail.message",
        "search_read",
        lambda *_: [{"id": 1, "date": "2026-06-17", "body": "<p>Called <b>them</b></p>"}],
    )
    result = runner.invoke(main.app, ["-f", "table", "crm", "leads", "messages", "50"])
    assert result.exit_code == 0, result.output
    assert "Called them" in result.output
    assert "<p>" not in result.output


def test_leads_messages_json_keeps_raw_html(wire):
    wire.route(
        "mail.message",
        "search_read",
        lambda *_: [{"id": 1, "body": "<p>raw</p>"}],
    )
    result = runner.invoke(main.app, ["--json", "crm", "leads", "messages", "50"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["body"] == "<p>raw</p>"


def test_leads_note_posts_internal_note(wire):
    wire.route("crm.lead", "message_post", lambda *_: 321)
    result = runner.invoke(
        main.app, ["--json", "crm", "leads", "note", "7", "--body", "Spoke to client"]
    )
    assert result.exit_code == 0, result.output
    req = next(r for r in wire.requests if r["method"] == "message_post")
    assert req["body"]["subtype_xmlid"] == "mail.mt_note"
    assert req["body"]["body"] == "Spoke to client"
    assert json.loads(result.output)["message_id"] == 321


def test_leads_note_dry_run_does_not_send(wire):
    result = runner.invoke(main.app, ["--dry-run", "crm", "leads", "note", "7", "--body", "x"])
    assert result.exit_code == 0, result.output
    assert wire.requests == []


def test_users_list(wire):
    wire.route(
        "res.users",
        "search_read",
        lambda *_: [{"id": 1, "name": "Jane", "login": "jane", "email": "j@x.com"}],
    )
    result = runner.invoke(main.app, ["--json", "users", "list", "--search", "ja"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["login"] == "jane"
