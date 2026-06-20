"""Base class for model resources.

Resources are the only place that knows which JSON-2 *method names* map to CRUD. Each
concrete resource (e.g. :class:`~odoo_cli.resources.crm_lead.CrmLead`) sets ``model`` and
adds high-level, typed methods on top of these thin wrappers.
"""

from __future__ import annotations

from typing import Any, ClassVar

from ..client import OdooClient

Domain = list[Any]

# Chatter (Odoo's mail.thread) lives in mail.message records linked by (model, res_id).
MAIL_MESSAGE = "mail.message"
MESSAGE_FIELDS = [
    "id",
    "date",
    "author_id",
    "email_from",
    "message_type",
    "subtype_id",
    "subject",
    "body",
]
# Internal log note vs. a message that notifies followers.
SUBTYPE_NOTE = "mail.mt_note"
SUBTYPE_COMMENT = "mail.mt_comment"


class Resource:
    """Thin typed wrapper over the generic ORM methods for a single model."""

    model: ClassVar[str]

    def __init__(self, client: OdooClient) -> None:
        self.client = client

    def search_read(
        self,
        domain: Domain | None = None,
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"domain": domain or []}
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if offset is not None:
            kwargs["offset"] = offset
        if order is not None:
            kwargs["order"] = order
        return self.client.call(self.model, "search_read", **kwargs)

    def read(self, ids: list[int], *, fields: list[str] | None = None) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"ids": ids}
        if fields is not None:
            kwargs["fields"] = fields
        return self.client.call(self.model, "read", **kwargs)

    def create(self, vals: dict[str, Any]) -> int:
        # JSON-2 `create` expects `vals_list` (a list of dicts) and returns a list of ids.
        result = self.client.call(self.model, "create", vals_list=[vals])
        return result[0] if isinstance(result, list) else result

    def write(self, ids: list[int], vals: dict[str, Any]) -> bool:
        return self.client.call(self.model, "write", ids=ids, vals=vals)

    # --- Chatter (generic to any mail.thread record) -------------------------------------

    def messages(
        self, record_id: int, *, limit: int = 20, order: str = "date desc"
    ) -> list[dict[str, Any]]:
        """Return this record's chatter messages (newest first), as raw mail.message records."""
        domain: Domain = [("model", "=", self.model), ("res_id", "=", record_id)]
        return self.client.call(
            MAIL_MESSAGE,
            "search_read",
            domain=domain,
            fields=MESSAGE_FIELDS,
            limit=limit,
            order=order,
        )

    def post_note(
        self, record_id: int, body: str, *, note: bool = True, subject: str | None = None
    ) -> int:
        """Post a chatter entry on this record and return the new mail.message id.

        ``note=True`` logs an internal note (mail.mt_note); ``note=False`` posts a message
        that notifies followers (mail.mt_comment).
        """
        kwargs: dict[str, Any] = {
            "ids": [record_id],
            "body": body,
            "message_type": "comment",
            "subtype_xmlid": SUBTYPE_NOTE if note else SUBTYPE_COMMENT,
        }
        if subject:
            kwargs["subject"] = subject
        result = self.client.call(self.model, "message_post", **kwargs)
        return _as_id(result)


def _as_id(result: Any) -> int:
    """Normalise message_post's return (int / [int] / {'id': int}) to a single id."""
    if isinstance(result, bool) or result is None:
        return 0
    if isinstance(result, int):
        return result
    if isinstance(result, list) and result:
        return _as_id(result[0])
    if isinstance(result, dict):
        return int(result.get("id", 0))
    return 0
