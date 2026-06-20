"""Transport-level tests: URL/header/body construction, error mapping, dry-run."""

from __future__ import annotations

import pytest

from odoo_cli.client import OdooClient
from odoo_cli.exceptions import AuthError, DryRun, NotFoundError, OdooError


def test_call_builds_url_headers_and_body(client, backend):
    backend.route("crm.lead", "search_read", lambda *_: [{"id": 1}])
    result = client.call("crm.lead", "search_read", domain=[], fields=["id"], limit=5)

    assert result == [{"id": 1}]
    req = backend.requests[-1]
    assert req["model"] == "crm.lead"
    assert req["method"] == "search_read"
    assert req["body"] == {"domain": [], "fields": ["id"], "limit": 5}
    assert req["headers"]["authorization"] == "bearer test-key"
    assert req["headers"]["x-odoo-database"] == "demo"


def test_no_db_header_when_db_unset(backend):
    client = OdooClient("https://demo.example.com", "k", transport=backend.transport())
    backend.route("res.users", "search_read", lambda *_: [])
    client.call("res.users", "search_read", domain=[])
    assert "x-odoo-database" not in backend.requests[-1]["headers"]


def test_401_maps_to_auth_error(client, backend):
    backend.fail("crm.lead", "search_read", 401, {"error": {"message": "bad key"}})
    with pytest.raises(AuthError, match="bad key"):
        client.call("crm.lead", "search_read", domain=[])


def test_404_maps_to_not_found(client, backend):
    backend.fail("crm.lead", "nope", 404, {"error": {"message": "no method"}})
    with pytest.raises(NotFoundError):
        client.call("crm.lead", "nope")


def test_500_maps_to_generic_error(client, backend):
    backend.fail("crm.lead", "create", 500, {"error": {"data": {"message": "boom"}}})
    with pytest.raises(OdooError, match="boom"):
        client.call("crm.lead", "create", vals={})


def test_dry_run_raises_without_sending(backend, capsys):
    client = OdooClient(
        "https://demo.example.com", "k", db="demo", dry_run=True, transport=backend.transport()
    )
    with pytest.raises(DryRun):
        client.call("crm.lead", "create", vals={"name": "x"})
    assert backend.requests == []  # nothing was sent
    err = capsys.readouterr().err
    assert "dry-run" in err
    assert "crm.lead/create" in err
