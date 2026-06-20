"""`oc users ...` commands."""

from __future__ import annotations

from typing import Annotated, cast

import typer

from .. import render
from ..resources import ResUsers
from ._errors import handle_errors

app = typer.Typer(name="users", help="Query Odoo users.", no_args_is_help=True)

LIST_COLUMNS = ["id", "name", "login", "email"]


@app.command("list")
@handle_errors
def list_users(
    ctx: typer.Context,
    search: Annotated[
        str | None, typer.Option("--search", "-s", help="Filter by name/login substring.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max rows.")] = 50,
) -> None:
    """List users, optionally filtered by name/login."""
    from .main import AppContext

    app_ctx = cast(AppContext, ctx.obj)
    rows = ResUsers(app_ctx.client).search(search, limit=limit)
    render.render(rows, app_ctx.fmt, columns=LIST_COLUMNS, title="Users")
