"""A decorator that turns SDK exceptions into clean CLI output + exit codes.

Applied to every command so error handling is consistent whether the CLI is run via the
``oc`` entry point or driven by Typer's ``CliRunner`` in tests.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

import typer

from .. import render
from ..exceptions import AmbiguousMatchError, DryRun, OdooError


def handle_errors[F: Callable[..., Any]](func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except DryRun as exc:
            raise typer.Exit(code=0) from exc
        except AmbiguousMatchError as exc:
            render.error(str(exc))
            for cand in exc.candidates:
                render.console.print(
                    f"  [cyan]{cand.get('id')}[/]  {cand.get('name')}  <{cand.get('login')}>"
                )
            raise typer.Exit(code=1) from exc
        except OdooError as exc:
            render.error(str(exc))
            raise typer.Exit(code=1) from exc

    return wrapper  # type: ignore[return-value]
