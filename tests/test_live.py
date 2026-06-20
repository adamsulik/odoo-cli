"""Opt-in live smoke test against a real Odoo 19 instance.

Skipped unless ``ODOO_CLI_LIVE=1`` and connection env vars are set:

    ODOO_CLI_LIVE=1 ODOO_URL=https://you.odoo.com ODOO_API_KEY=... \
        [ODOO_DB=...] uv run pytest tests/test_live.py -v

It only reads data (lists users and leads); it never writes.
"""

from __future__ import annotations

import os

import pytest

from odoo_cli.config import resolve
from odoo_cli.resources import CrmLead, ResUsers

pytestmark = pytest.mark.skipif(
    os.environ.get("ODOO_CLI_LIVE") != "1",
    reason="set ODOO_CLI_LIVE=1 (and ODOO_URL/ODOO_API_KEY) to run live tests",
)


@pytest.fixture
def live_client():
    from odoo_cli.client import OdooClient

    profile = resolve(None)
    client = OdooClient(profile.host, profile.api_key or "", db=profile.db)
    yield client
    client.close()


def test_users_list_live(live_client):
    users = ResUsers(live_client).search(limit=5)
    assert isinstance(users, list)
    if users:
        assert "login" in users[0]


def test_leads_list_live(live_client):
    leads = CrmLead(live_client).list(limit=5)
    assert isinstance(leads, list)
