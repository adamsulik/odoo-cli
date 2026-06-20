"""`oc crm leads ...` commands."""

from __future__ import annotations

from typing import Annotated, cast

import typer

from .. import render
from ..exceptions import OdooError
from ..resources import CrmLead, ResUsers
from ._errors import handle_errors

app = typer.Typer(name="crm", help="CRM commands.", no_args_is_help=True)
leads = typer.Typer(name="leads", help="Work with CRM leads.", no_args_is_help=True)
app.add_typer(leads, name="leads")

LIST_COLUMNS = [
    "id",
    "name",
    "contact_name",
    "email_from",
    "stage_id",
    "user_id",
    "expected_revenue",
]

MESSAGE_COLUMNS = ["id", "date", "author_id", "message_type", "subject", "body"]


def _ctx(ctx: typer.Context):
    from .main import AppContext

    return cast(AppContext, ctx.obj)


def _resolve_me(app_ctx) -> int:
    """Resolve the profile's own login to a user id for --mine."""
    login = app_ctx.profile.login
    if not login:
        raise OdooError(
            "--mine needs your login stored in the profile. "
            "Re-run `oc login` (it now asks for your login) or use --user <you>."
        )
    return ResUsers(app_ctx.client).resolve(login)


@leads.command("list")
@handle_errors
def list_leads(
    ctx: typer.Context,
    mine: Annotated[bool, typer.Option("--mine", help="Only leads assigned to me.")] = False,
    user: Annotated[
        str | None, typer.Option("--user", "-u", help="Filter by salesperson (name/login/id).")
    ] = None,
    stage: Annotated[str | None, typer.Option("--stage", help="Filter by stage name.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max rows.")] = 20,
    order: Annotated[str, typer.Option("--order", help="Sort order.")] = "create_date desc",
) -> None:
    """List leads with optional filters."""
    app_ctx = _ctx(ctx)
    res = CrmLead(app_ctx.client)
    user_id: int | None = None
    if mine:
        user_id = _resolve_me(app_ctx)
    elif user:
        user_id = ResUsers(app_ctx.client).resolve(user)
    rows = res.list(user_id=user_id, stage=stage, limit=limit, order=order)
    render.render(rows, app_ctx.fmt, columns=LIST_COLUMNS, title="CRM leads")


@leads.command("get")
@handle_errors
def get_lead(
    ctx: typer.Context,
    lead_id: Annotated[int, typer.Argument(help="Lead id.")],
) -> None:
    """Show a single lead."""
    app_ctx = _ctx(ctx)
    record = CrmLead(app_ctx.client).get(lead_id)
    render.render(record, app_ctx.fmt, title=f"Lead {lead_id}")


@leads.command("create")
@handle_errors
def create_lead(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Lead/opportunity title.")],
    contact: Annotated[str | None, typer.Option("--contact", help="Contact name.")] = None,
    email: Annotated[str | None, typer.Option("--email", help="Email.")] = None,
    phone: Annotated[str | None, typer.Option("--phone", help="Phone.")] = None,
    expected_revenue: Annotated[
        float | None, typer.Option("--expected-revenue", help="Expected revenue.")
    ] = None,
    user: Annotated[
        str | None, typer.Option("--user", "-u", help="Assign salesperson (name/login/id).")
    ] = None,
    description: Annotated[str | None, typer.Option("--description", help="Notes.")] = None,
    lead_type: Annotated[str, typer.Option("--type", help="lead or opportunity.")] = "lead",
) -> None:
    """Create a new lead."""
    app_ctx = _ctx(ctx)
    res = CrmLead(app_ctx.client)
    user_id = ResUsers(app_ctx.client).resolve(user) if user else None
    record = res.create(
        name,
        contact=contact,
        email=email,
        phone=phone,
        expected_revenue=expected_revenue,
        user_id=user_id,
        description=description,
        lead_type=lead_type,
    )
    render.render(record, app_ctx.fmt, title="Created lead")


@leads.command("assign")
@handle_errors
def assign_lead(
    ctx: typer.Context,
    lead_id: Annotated[int, typer.Argument(help="Lead id.")],
    user: Annotated[str, typer.Option("--user", "-u", help="Salesperson (name/login/id).")],
) -> None:
    """Assign a lead to a user."""
    app_ctx = _ctx(ctx)
    user_id = ResUsers(app_ctx.client).resolve(user)
    record = CrmLead(app_ctx.client).assign(lead_id, user_id)
    render.render(record, app_ctx.fmt, title=f"Lead {lead_id} assigned")


@leads.command("messages")
@handle_errors
def lead_messages(
    ctx: typer.Context,
    lead_id: Annotated[int, typer.Argument(help="Lead id.")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max messages.")] = 20,
) -> None:
    """Show a lead's chatter messages (newest first)."""
    app_ctx = _ctx(ctx)
    rows = CrmLead(app_ctx.client).messages(lead_id, limit=limit)
    if app_ctx.fmt is not render.Format.JSON:
        # Flatten chatter HTML to plain text for table/csv display; JSON keeps it raw.
        rows = [{**row, "body": render.html_to_text(row.get("body"))} for row in rows]
    render.render(rows, app_ctx.fmt, columns=MESSAGE_COLUMNS, title=f"Lead {lead_id} chatter")


@leads.command("note")
@handle_errors
def lead_note(
    ctx: typer.Context,
    lead_id: Annotated[int, typer.Argument(help="Lead id.")],
    body: Annotated[str, typer.Option("--body", "-b", help="Note text (HTML allowed).")],
    subject: Annotated[str | None, typer.Option("--subject", help="Optional subject.")] = None,
    message: Annotated[
        bool,
        typer.Option("--message", help="Post as a message that notifies followers (not a note)."),
    ] = False,
) -> None:
    """Log an internal note on a lead (or a follower-notifying message with --message)."""
    app_ctx = _ctx(ctx)
    res = CrmLead(app_ctx.client)
    message_id = res.post_note(lead_id, body, note=not message, subject=subject)
    kind = "Message" if message else "Note"
    render.render(
        {"lead_id": lead_id, "message_id": message_id, "posted": kind},
        app_ctx.fmt,
        title=f"{kind} posted",
    )
