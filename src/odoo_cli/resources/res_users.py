"""``res.users`` resource: listing and name/login -> id resolution."""

from __future__ import annotations

from typing import Any

from ..exceptions import AmbiguousMatchError, NotFoundError
from .base import Resource

LIST_FIELDS = ["id", "name", "login", "email"]


class ResUsers(Resource):
    model = "res.users"

    def search(self, query: str | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
        """List active users, optionally filtered by a name/login substring."""
        domain: list[Any] = []
        if query:
            domain = ["|", ("name", "ilike", query), ("login", "ilike", query)]
        return self.search_read(domain, fields=LIST_FIELDS, limit=limit, order="name")

    def resolve(self, query: str | int) -> int:
        """Resolve a user reference to a numeric id.

        Accepts a raw id (int or digit string), or a name/login matched case-insensitively.
        Raises :class:`NotFoundError` on no match and :class:`AmbiguousMatchError` on >1.
        """
        if isinstance(query, int):
            return query
        text = query.strip()
        if text.isdigit():
            return int(text)

        domain: list[Any] = ["|", ("login", "=ilike", text), ("name", "ilike", text)]
        matches = self.search_read(domain, fields=LIST_FIELDS, limit=10, order="name")
        if not matches:
            raise NotFoundError(f"No user matching '{query}'.")
        if len(matches) > 1:
            # Prefer an exact login match if one stands out.
            exact = [m for m in matches if str(m.get("login", "")).lower() == text.lower()]
            if len(exact) == 1:
                return int(exact[0]["id"])
            raise AmbiguousMatchError(
                f"'{query}' matches {len(matches)} users; be more specific or pass the id.",
                candidates=matches,
            )
        return int(matches[0]["id"])
