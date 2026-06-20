# odoo-cli (`oc`)

A human-friendly command-line tool for driving an **Odoo 19** database from the terminal,
built on Odoo's **External JSON-2 API** (`POST /json/2/<model>/<method>`, bearer API key).

It is also an importable Python SDK: `OdooClient` plus one resource class per model, so the
CLI is a thin layer you can reuse from scripts.

## Install

```bash
uv sync
uv run oc --help
```

## Configure

```bash
uv run oc login            # prompts for host URL, database (if multi-db), your login, API key
uv run oc profiles         # list configured profiles
```

Profiles (host/db/login) live in `~/.config/odoo-cli/config.toml`. The **API key is stored in
your OS keyring**, never in the file. Everything can be overridden by environment variables
(`ODOO_URL`, `ODOO_DB`, `ODOO_API_KEY`, `ODOO_PROFILE`) for CI use.

Generate an API key in Odoo under *Preferences → Account Security → New API Key*.

## Commands (v1)

```bash
oc crm leads list [--mine] [--user NAME] [--stage NAME] [--limit N]
oc crm leads get <id>
oc crm leads create --name "Big deal" [--user NAME] [--email ...] [--expected-revenue 1000]
oc crm leads assign <id> --user "Jane Doe"
oc users list [--search NAME]
```

Global options: `--profile/-p`, `--format/-f {table,json,csv}` (or `--json`), `--dry-run`.
Output is a Rich table on a TTY and JSON when piped. `--dry-run` prints the exact JSON-2
request without sending it.

## Develop

Set up a dev environment once — this syncs the dev dependency group and installs the git
hooks (`pre-commit` + `commit-msg`):

```bash
make setup        # uv sync --dev && pre-commit install --install-hooks
```

Common tasks have `make` shortcuts (each shells out to `uv run`, so versions follow
`uv.lock`):

```bash
make ruff         # lint with ruff (auto-fix)
make format       # auto-format with ruff
make pyright      # type-check
make test         # run the unit test suite
make check        # run every pre-commit hook on all files
```

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/) — the
`commit-msg` hook (commitizen) enforces this. Use `uv run cz commit` for a guided message and
`uv run cz bump` to tag a release. Prefer plain `make`/`uv` over global tool installs.

The package is layered as an importable core (`client.py` → `resources/`) under a thin Typer
CLI (`cli/`), so adding new resources/commands (sales orders, projects, …) is mechanical.
