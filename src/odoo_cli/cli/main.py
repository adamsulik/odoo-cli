"""Root Typer app: global options, context wiring, and error handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import typer

from .. import config, render
from ..client import OdooClient
from ..config import Profile
from ..render import Format
from . import config_cmd, crm, users


@dataclass
class AppContext:
    """Shared state attached to ``ctx.obj`` for every command.

    Profile resolution and client construction are both lazy, so ``--help`` at any level
    and the ``login``/``profiles`` commands never require a configured profile.
    """

    profile_name: str | None
    fmt: Format
    dry_run: bool
    _profile: Profile | None = None
    _client: OdooClient | None = None

    @property
    def profile(self) -> Profile:
        if self._profile is None:
            self._profile = config.resolve(self.profile_name)
        return self._profile

    @property
    def client(self) -> OdooClient:
        if self._client is None:
            self._client = OdooClient(
                self.profile.host,
                self.profile.api_key or "",
                db=self.profile.db,
                dry_run=self.dry_run,
            )
        return self._client


app = typer.Typer(
    name="oc",
    help="Drive an Odoo 19 database from the terminal (External JSON-2 API).",
    no_args_is_help=True,
    add_completion=True,
)
app.add_typer(crm.app, name="crm")
app.add_typer(users.app, name="users")
app.command("login")(config_cmd.login)
app.command("profiles")(config_cmd.profiles)


@app.callback()
def main(
    ctx: typer.Context,
    profile: Annotated[
        str | None, typer.Option("--profile", "-p", help="Connection profile to use.")
    ] = None,
    fmt: Annotated[
        Format | None,
        typer.Option("--format", "-f", help="Output format (default: table on a TTY, else json)."),
    ] = None,
    json_: Annotated[
        bool, typer.Option("--json", help="Shorthand for --format json.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print the request that would be sent, then exit.")
    ] = False,
) -> None:
    chosen = Format.JSON if json_ else fmt
    ctx.obj = AppContext(
        profile_name=profile, fmt=render.resolve_format(chosen), dry_run=dry_run
    )


def run() -> None:
    """Entry point. Per-command errors are handled by the ``@handle_errors`` decorator;
    this is just the Typer app invocation."""
    app()


if __name__ == "__main__":
    run()
