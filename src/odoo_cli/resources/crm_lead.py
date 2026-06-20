"""``crm.lead`` resource: list / get / create / assign."""

from __future__ import annotations

from typing import Any

from .base import Resource

# Columns for the list view (compact) and the single-record view (fuller).
LIST_FIELDS = [
    "id",
    "name",
    "contact_name",
    "partner_name",
    "email_from",
    "stage_id",
    "user_id",
    "expected_revenue",
]
DETAIL_FIELDS = [
    *LIST_FIELDS,
    "phone",
    "team_id",
    "type",
    "probability",
    "description",
    "create_date",
]


class CrmLead(Resource):
    model = "crm.lead"

    def list(
        self,
        *,
        user_id: int | None = None,
        stage: str | None = None,
        limit: int = 20,
        order: str = "create_date desc",
    ) -> list[dict[str, Any]]:
        """List leads, composing a JSON-2 domain from the given filters."""
        domain: list[Any] = []
        if user_id is not None:
            domain.append(("user_id", "=", user_id))
        if stage:
            domain.append(("stage_id.name", "ilike", stage))
        return self.search_read(domain, fields=LIST_FIELDS, limit=limit, order=order)

    def get(self, lead_id: int) -> dict[str, Any]:
        """Read a single lead's detail fields."""
        records = self.read([lead_id], fields=DETAIL_FIELDS)
        if not records:
            from ..exceptions import NotFoundError

            raise NotFoundError(f"No lead with id {lead_id}.")
        return records[0]

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        contact: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        expected_revenue: float | None = None,
        user_id: int | None = None,
        description: str | None = None,
        lead_type: str = "lead",
    ) -> dict[str, Any]:
        """Create a lead from explicit fields and return the created record."""
        vals: dict[str, Any] = {"name": name, "type": lead_type}
        if contact is not None:
            vals["contact_name"] = contact
        if email is not None:
            vals["email_from"] = email
        if phone is not None:
            vals["phone"] = phone
        if expected_revenue is not None:
            vals["expected_revenue"] = expected_revenue
        if user_id is not None:
            vals["user_id"] = user_id
        if description is not None:
            vals["description"] = description
        new_id = super().create(vals)
        return self.get(int(new_id))

    def assign(self, lead_id: int, user_id: int) -> dict[str, Any]:
        """Set the salesperson (``user_id``) on a lead and return the refreshed record."""
        self.write([lead_id], {"user_id": user_id})
        return self.get(lead_id)
