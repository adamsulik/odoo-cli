"""CrmLead resource: domain building, create vals, assign."""

from __future__ import annotations

from odoo_cli.resources import CrmLead


def test_list_builds_domain_from_filters(client, backend):
    backend.route("crm.lead", "search_read", lambda *_: [{"id": 1, "name": "A"}])
    CrmLead(client).list(user_id=7, stage="Won", limit=10, order="id desc")

    body = backend.requests[-1]["body"]
    assert body["domain"] == [["user_id", "=", 7], ["stage_id.name", "ilike", "Won"]]
    assert body["limit"] == 10
    assert body["order"] == "id desc"
    assert "user_id" in body["fields"]


def test_list_empty_domain_when_no_filters(client, backend):
    backend.route("crm.lead", "search_read", lambda *_: [])
    CrmLead(client).list()
    assert backend.requests[-1]["body"]["domain"] == []


def test_create_builds_vals_and_refetches(client, backend):
    backend.route("crm.lead", "create", lambda *_: 42)
    backend.route("crm.lead", "read", lambda *_: [{"id": 42, "name": "Deal"}])

    record = CrmLead(client).create(
        "Deal", email="x@y.com", expected_revenue=1000.0, user_id=3
    )

    create_body = backend.requests[-2]["body"]
    assert create_body["vals"] == {
        "name": "Deal",
        "type": "lead",
        "email_from": "x@y.com",
        "expected_revenue": 1000.0,
        "user_id": 3,
    }
    # Second call reads the new record back.
    assert backend.requests[-1]["body"]["ids"] == [42]
    assert record == {"id": 42, "name": "Deal"}


def test_messages_queries_mail_message_by_model_and_res_id(client, backend):
    backend.route(
        "mail.message",
        "search_read",
        lambda *_: [{"id": 1, "body": "<p>hi</p>", "author_id": [3, "Jane"]}],
    )
    rows = CrmLead(client).messages(50, limit=5)

    body = backend.requests[-1]["body"]
    assert body["domain"] == [["model", "=", "crm.lead"], ["res_id", "=", 50]]
    assert body["limit"] == 5
    assert body["order"] == "date desc"
    assert rows[0]["body"] == "<p>hi</p>"  # SDK returns raw HTML


def test_post_note_logs_internal_note(client, backend):
    backend.route("crm.lead", "message_post", lambda *_: 123)
    message_id = CrmLead(client).post_note(7, "Called the client")

    body = backend.requests[-1]["body"]
    assert body["ids"] == [7]
    assert body["body"] == "Called the client"
    assert body["message_type"] == "comment"
    assert body["subtype_xmlid"] == "mail.mt_note"
    assert message_id == 123


def test_post_note_as_message_uses_comment_subtype(client, backend):
    backend.route("crm.lead", "message_post", lambda *_: [55])
    message_id = CrmLead(client).post_note(7, "FYI", note=False, subject="Update")

    body = backend.requests[-1]["body"]
    assert body["subtype_xmlid"] == "mail.mt_comment"
    assert body["subject"] == "Update"
    assert message_id == 55  # [int] normalised to int


def test_assign_writes_user_id(client, backend):
    written: dict = {}

    def on_write(_m, _meth, body):
        written.update(body)
        return True

    backend.route("crm.lead", "write", on_write)
    backend.route("crm.lead", "read", lambda *_: [{"id": 5, "user_id": [3, "Jane"]}])

    record = CrmLead(client).assign(5, 3)
    assert written == {"ids": [5], "vals": {"user_id": 3}}
    assert record["user_id"] == [3, "Jane"]
