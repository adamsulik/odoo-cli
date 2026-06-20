"""Output rendering: Rich tables/panels for humans, JSON/CSV for machines.

Odoo many2one fields come back as ``[id, "Display Name"]``; in table/panel mode we show the
name, while JSON/CSV keep the raw value so downstream tooling can use the id.
"""

from __future__ import annotations

import csv
import enum
import html
import io
import json
import re
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]*\n[ \t]*")


class Format(enum.StrEnum):
    TABLE = "table"
    JSON = "json"
    CSV = "csv"


def resolve_format(explicit: Format | None) -> Format:
    """Pick the output format: explicit flag wins; else table on a TTY, JSON when piped."""
    if explicit is not None:
        return explicit
    return Format.TABLE if sys.stdout.isatty() else Format.JSON


def _display(value: Any) -> str:
    """Human display for a single cell, unwrapping many2one ``[id, name]`` pairs."""
    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
        return str(value[1])
    if value is False or value is None:
        return ""
    return str(value)


def render(
    data: dict[str, Any] | list[dict[str, Any]],
    fmt: Format,
    *,
    columns: list[str] | None = None,
    title: str | None = None,
) -> None:
    """Render ``data`` (a record or list of records) to stdout in the chosen format."""
    if fmt is Format.JSON:
        console.print_json(json.dumps(data, default=str))
        return
    if fmt is Format.CSV:
        _render_csv(data, columns)
        return

    if isinstance(data, dict):
        _render_panel(data, title=title)
    else:
        _render_table(data, columns=columns, title=title)


def _render_table(
    rows: list[dict[str, Any]], *, columns: list[str] | None, title: str | None
) -> None:
    if not rows:
        console.print("[dim]No records found.[/]")
        return
    cols = columns or list(rows[0].keys())
    table = Table(title=title, show_lines=False, header_style="bold cyan")
    for col in cols:
        table.add_column(col)
    for row in rows:
        table.add_row(*[_display(row.get(col)) for col in cols])
    console.print(table)


def _render_panel(record: dict[str, Any], *, title: str | None) -> None:
    cols = max((len(k) for k in record), default=0)
    lines = [f"[bold]{k:<{cols}}[/]  {_display(v)}" for k, v in record.items()]
    console.print(Panel("\n".join(lines), title=title, border_style="cyan", expand=False))


def _render_csv(data: dict[str, Any] | list[dict[str, Any]], columns: list[str] | None) -> None:
    rows = [data] if isinstance(data, dict) else data
    if not rows:
        return
    cols = columns or list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: _csv_value(row.get(c)) for c in cols})
    sys.stdout.write(buf.getvalue())


def _csv_value(value: Any) -> Any:
    """Keep raw values for CSV, but flatten many2one pairs to their display name."""
    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
        return value[1]
    if value is False or value is None:
        return ""
    return value


def html_to_text(value: Any) -> str:
    """Flatten Odoo chatter HTML to readable plain text for table/panel display."""
    if not value or not isinstance(value, str):
        return ""
    text = value.replace("<br>", "\n").replace("<br/>", "\n").replace("</p>", "\n")
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _WS_RE.sub("\n", text)
    return text.strip()


def error(message: str) -> None:
    """Print a clean error line to stderr."""
    Console(stderr=True).print(f"[bold red]error:[/] {message}")
