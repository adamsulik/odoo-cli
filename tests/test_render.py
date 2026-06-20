"""Renderer tests: format resolution, JSON/CSV output, many2one unwrapping."""

from __future__ import annotations

import json

from odoo_cli import render
from odoo_cli.render import Format


def test_resolve_format_explicit_wins(monkeypatch):
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert render.resolve_format(Format.CSV) is Format.CSV


def test_resolve_format_tty_defaults_table(monkeypatch):
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert render.resolve_format(None) is Format.TABLE


def test_resolve_format_pipe_defaults_json(monkeypatch):
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    assert render.resolve_format(None) is Format.JSON


def test_render_json_outputs_raw_values(capsys):
    render.render([{"id": 1, "user_id": [3, "Jane"]}], Format.JSON)
    out = json.loads(capsys.readouterr().out)
    assert out == [{"id": 1, "user_id": [3, "Jane"]}]  # m2o pair preserved


def test_render_csv_flattens_many2one(capsys):
    render.render([{"id": 1, "user_id": [3, "Jane"]}], Format.CSV, columns=["id", "user_id"])
    out = capsys.readouterr().out
    assert "id,user_id" in out
    assert "1,Jane" in out


def test_render_table_unwraps_and_shows(capsys):
    render.render([{"id": 1, "user_id": [3, "Jane"], "x": False}], Format.TABLE)
    out = capsys.readouterr().out
    assert "Jane" in out


def test_html_to_text_strips_tags_and_unescapes():
    assert render.html_to_text("<p>Hello&nbsp;<b>world</b></p>") == "Hello world"
    assert render.html_to_text("a<br>b") == "a\nb"
    assert render.html_to_text(False) == ""
    assert render.html_to_text(None) == ""
