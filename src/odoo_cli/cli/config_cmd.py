"""`oc login` and `oc profiles` — manage connection profiles and stored keys."""

from __future__ import annotations

from typing import Annotated

import typer

from .. import config, render


def login(
    profile: Annotated[
        str, typer.Option("--profile", "-p", help="Profile name to create/update.")
    ] = "default",
    host: Annotated[
        str | None, typer.Option("--host", help="Base URL, e.g. https://co.odoo.com")
    ] = None,
    db: Annotated[
        str | None, typer.Option("--db", help="Database name (multi-db hosts only).")
    ] = None,
    login_name: Annotated[
        str | None, typer.Option("--login", help="Your Odoo login (enables --mine).")
    ] = None,
    make_default: Annotated[
        bool, typer.Option("--default/--no-default", help="Make this the default profile.")
    ] = True,
) -> None:
    """Store a connection profile and its API key (key goes to the OS keyring)."""
    resolved_host: str = host or typer.prompt("Odoo host URL (e.g. https://mycompany.odoo.com)")
    if db is None:
        db = typer.prompt("Database (blank if single-db)", default="", show_default=False) or None
    if login_name is None:
        prompt = "Your login (blank to skip --mine support)"
        login_name = typer.prompt(prompt, default="", show_default=False) or None
    api_key = typer.prompt("API key", hide_input=True)

    config.save_profile(profile, resolved_host, db, login=login_name, make_default=make_default)
    config.save_api_key(profile, api_key)
    render.console.print(
        f"[green]Saved[/] profile [bold]{profile}[/] -> {resolved_host.rstrip('/')}"
        + (f" (db={db})" if db else "")
    )


def profiles() -> None:
    """List configured profiles."""
    cfg = config.load_config()
    if not cfg.profiles:
        render.console.print("[dim]No profiles configured. Run `oc login`.[/]")
        return
    rows = [
        {
            "name": p.name,
            "host": p.host,
            "db": p.db or "",
            "login": p.login or "",
            "default": "*" if p.name == cfg.default else "",
        }
        for p in cfg.profiles.values()
    ]
    render.render(rows, render.Format.TABLE, title="Profiles")
