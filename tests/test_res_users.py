"""ResUsers.resolve: id / unique / none / ambiguous."""

from __future__ import annotations

import pytest

from odoo_cli.exceptions import AmbiguousMatchError, NotFoundError
from odoo_cli.resources import ResUsers


def test_resolve_passes_through_int(client, backend):
    assert ResUsers(client).resolve(9) == 9
    assert backend.requests == []  # no lookup needed


def test_resolve_digit_string(client, backend):
    assert ResUsers(client).resolve("12") == 12
    assert backend.requests == []


def test_resolve_unique_name(client, backend):
    user = {"id": 4, "name": "Jane", "login": "jane"}
    backend.route("res.users", "search_read", lambda *_: [user])
    assert ResUsers(client).resolve("Jane") == 4


def test_resolve_none_raises(client, backend):
    backend.route("res.users", "search_read", lambda *_: [])
    with pytest.raises(NotFoundError):
        ResUsers(client).resolve("ghost")


def test_resolve_ambiguous_raises_with_candidates(client, backend):
    backend.route(
        "res.users",
        "search_read",
        lambda *_: [
            {"id": 1, "name": "Jan A", "login": "jana"},
            {"id": 2, "name": "Jan B", "login": "janb"},
        ],
    )
    with pytest.raises(AmbiguousMatchError) as exc:
        ResUsers(client).resolve("Jan")
    assert len(exc.value.candidates) == 2


def test_resolve_ambiguous_but_exact_login_wins(client, backend):
    backend.route(
        "res.users",
        "search_read",
        lambda *_: [
            {"id": 1, "name": "Jane Doe", "login": "jane"},
            {"id": 2, "name": "Jane Smith", "login": "jane.smith"},
        ],
    )
    assert ResUsers(client).resolve("jane") == 1
