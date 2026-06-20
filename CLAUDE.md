# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This project uses **uv** (Python ≥ 3.13). The CLI entry point is `oc` (= `odoo_cli.cli.main:run`).
Common dev tasks have `make` shortcuts (`make setup|ruff|format|pyright|test|check`); each just
wraps the `uv run` command below.

```bash
uv sync                       # install deps + dev tools
uv run oc --help              # run the CLI
uv run ruff check .           # lint (line-length 100; rules: E,F,I,UP,B,SIM)
uv run ruff format .          # auto-format (enforced in CI/pre-commit)
uv run pyright                # type-check (standard mode, src + tests)
uv run pytest                 # full unit test suite (mocked transport, no network)
uv run pytest tests/test_crm_lead.py::test_name -v   # single test
```

### Pre-commit / commit conventions

Hooks are defined in `.pre-commit-config.yaml`. After `uv sync`, enable them once per
clone:

```bash
uv run pre-commit install --install-hooks   # installs pre-commit + commit-msg hooks
uv run pre-commit run --all-files           # run everything on demand
```

- **`pre-commit` stage** runs `ruff check --fix`, `ruff format`, and `pyright` (plus
  whitespace/EOF/TOML hygiene). The lint/type hooks are **`language: system`** and shell out
  to `uv run`, so they use the exact versions pinned in `uv.lock` — there is no second,
  drifting tool install. `pyright` runs with `pass_filenames: false` because type-checking
  needs the whole package in view, not just the staged files.
- **`commit-msg` stage** runs **commitizen**, which enforces [Conventional
  Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, …). Config lives
  in `[tool.commitizen]` in `pyproject.toml` (`major_version_zero = true`; version sourced
  from `pep621` / `project.version`). Use `uv run cz commit` for a guided message, or
  `uv run cz bump` to tag a release and update the changelog.

Live smoke tests are **opt-in** and hit a real Odoo instance (read-only):

```bash
ODOO_CLI_LIVE=1 ODOO_URL=https://you.odoo.com ODOO_API_KEY=... [ODOO_DB=...] \
  uv run pytest tests/test_live.py -v
```

## Architecture

A layered SDK with a thin Typer CLI on top. The dependency direction is strictly
**`client` → `resources` → `cli`**; never reach upward.

- **`client.py` (`OdooClient`)** — the *only* module that knows the JSON-2 wire format.
  `client.call(model, method, **kwargs)` issues `POST {host}/json/2/{model}/{method}` with a
  bearer API key and (optionally) an `X-Odoo-Database` header. **JSON-2 has no positional
  args** — everything is passed by name. Handles retries (429/502/503/504), error-envelope
  extraction, and `dry_run` (renders the request and raises `DryRun` instead of sending).
  Inject `transport=httpx.MockTransport(...)` to fake the backend in tests.

- **`resources/`** — one class per Odoo model, the only place that maps high-level operations
  to ORM method names. `base.Resource` provides thin typed wrappers (`search_read`, `read`,
  `create`, `write`) plus generic **chatter** helpers (`messages`, `post_note`) that work on
  any `mail.thread` record via `mail.message`. Concrete resources (`CrmLead`, `ResUsers`) add
  domain-composing methods. Note JSON-2 quirks already handled here: `create` takes
  `vals_list=[...]` and returns a list of ids; `message_post` returns are normalised by
  `_as_id`.

- **`cli/`** — Typer apps mirroring the command tree. `main.py` defines global options
  (`--profile`, `--format/--json`, `--dry-run`) and stashes an **`AppContext`** on `ctx.obj`
  whose `profile`/`client` are **lazy** (so `--help`, `login`, and `profiles` never need a
  configured profile). Each command is wrapped with **`@handle_errors`** (`cli/_errors.py`),
  which converts SDK exceptions into clean stderr messages + exit codes and turns `DryRun`
  into a clean exit 0. Adding a resource/command is mechanical: add a resource class, then a
  Typer command that resolves args, calls the resource, and passes the result to `render`.

- **`render.py`** — output formatting. `Format` is `table` (Rich, default on a TTY), `json`
  (default when piped), or `csv`. Key convention: Odoo many2one fields arrive as
  `[id, "Display Name"]` — table/CSV show the **name**, JSON keeps the **raw** value so
  downstream tooling can use the id. `html_to_text` flattens chatter HTML for table/CSV.

- **`config.py`** — connection profiles. Profiles (host/db/login) live in
  `~/.config/odoo-cli/config.toml`; the **API key is stored in the OS keyring, never in the
  file**. Resolution order: explicit `--profile` → `ODOO_PROFILE` → config `default`; each of
  host/db/key can be overridden by `ODOO_URL`/`ODOO_DB`/`ODOO_API_KEY`, which makes the CLI
  usable with no config file at all (CI-friendly). The profile's `login` is captured at
  `oc login` time so `--mine` resolves "me" to a user id without a whoami call.

## Conventions

- Exceptions live in `exceptions.py` and all derive from `OdooError`
  (`AuthError`, `NotFoundError`, `AmbiguousMatchError`, `ConfigError`, `DryRun`). Raise these
  from resources/config; `@handle_errors` renders them. `AmbiguousMatchError` carries
  `candidates` so the CLI can list them.
- User references (`--user`, `--mine`) accept a name, login, or id and are resolved to an id
  via `ResUsers.resolve` (exact-login wins over multiple name matches; otherwise ambiguous).
- Tests use the `backend`/`client` fixtures in `conftest.py` (a `MockBackend` over
  `httpx.MockTransport`) — register per-`(model, method)` handlers; no network, no real config.
