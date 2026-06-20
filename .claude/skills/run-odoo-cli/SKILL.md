---
name: run-odoo-cli
description: Run and drive the odoo-cli (`oc`) tool to perform Odoo CRM tasks from the terminal — list/get/create/assign leads, update a lead, assign a salesperson, search users, post chatter notes. Use when asked to "run oc", "use odoo-cli", "assign a lead", "update a lead", or "look up an Odoo user". Assumes `oc` is already logged in.
---

# Drive odoo-cli (`oc`)

`oc` is a Typer CLI that drives a live Odoo 19 database over its JSON-2 HTTP API. It is
**already logged in** — a default profile and its API key (in the OS keyring) are
configured. There is no GUI and no separate driver: **the CLI itself is the harness.**
Run it with `uv run oc ...` from the repo root.

Paths below are relative to the repo root (the `odoo-cli/` directory).

## The one rule: get the exact id before you act

Every mutating command resolves a `--user "Name"` to a numeric id **before** writing, by
name/login match against `res.users`. A name can match zero users (error), one (proceeds),
or several (ambiguity error). **Never assume the match is the user you mean.** Before any
assign/create-with-owner, look the user up and confirm the id:

```bash
uv run oc --json users list --search admin
```

→ `[{"id": 2, "name": "Administrator", "login": "admin", "email": "adam@sulik.io"}]`

Confirm that id is the person you intend, then assign by that **exact login or id** (not a
loose name) so the resolution is unambiguous. The same goes for lead ids — list/get first:

```bash
uv run oc --json crm leads list --limit 3
```

→ returns leads with their `id`, `stage_id`, and current `user_id` as `[id, "Name"]` pairs.

## When unsure, ask the CLI — `--help` at every level

The command tree is self-documenting. Drill down before guessing flags:

```bash
uv run oc --help                  # top level: crm, users, login, profiles + global opts
uv run oc crm leads --help        # list, get, create, assign, messages, note
uv run oc crm leads assign --help # exact args/flags for one command
```

Global options (before the subcommand): `--profile/-p`, `--format/-f {table,json,csv}`,
`--json`, `--dry-run`.

## Preview any write with `--dry-run`

`--dry-run` renders the exact JSON-2 request to stderr and exits **without sending**. Use it
to confirm what a write will do before doing it for real:

```bash
uv run oc --dry-run crm leads assign 42 --user "Jane Doe"
```

**Gotcha:** for `assign`/`create --user`, the *first* JSON-2 call is the `res.users`
name→id lookup, and `--dry-run` exits at that first call — so it shows the **user-lookup
request, not the final write**. That is by design: it confirms how the name resolves. To
actually perform the write, drop `--dry-run`.

## Recipe: assign / update a lead to a specific user

The discipline the whole skill is about — resolve, verify, then act:

```bash
# 1. Find the user and confirm the id is who you mean.
uv run oc --json users list --search jane          # note the id, e.g. 7

# 2. Check the lead's current state (id + current owner).
uv run oc --json crm leads get 42

# 3. Preview the request (shows the res.users resolution).
uv run oc --dry-run crm leads assign 42 --user jane

# 4. Execute — assign by the unambiguous login (or the bare id) you verified in step 1.
uv run oc --json crm leads assign 42 --user jane
```

`assign` writes `user_id` then re-reads the lead, so its output is the refreshed record —
check `user_id` in it equals the id you expected. Other writes follow the same shape:
`create` (`--name` required, optional `--user/--email/--expected-revenue/...`) and
`note <lead_id> --body "..."` (internal note; add `--message` to notify followers).

## Run (verified commands)

These were all run against the live demo Odoo this session and worked:

```bash
uv run oc profiles                            # shows the logged-in default profile
uv run oc --json users list --limit 5         # read-only
uv run oc --json crm leads list --limit 3     # read-only
uv run oc --json users list --search admin    # read-only
```

Read-only commands (`profiles`, `users list`, `crm leads list/get/messages`) are safe to
run anytime. Writes (`create`, `assign`, `note`) change real data — dry-run first.

## Output format

Table (Rich) on a TTY, **JSON when piped or scripted** (the default off-TTY). Pass `--json`
explicitly when you need to parse output. Many2one fields come back as `[id, "Name"]` in
JSON — use the `[0]` element when you need the id, the `[1]` for display.

## Gotchas

- **`--user` is fuzzy until it isn't.** A name like `"Jan"` can match several users and
  the command exits 1 with `'Jan' matches N users; be more specific or pass the id`. Always
  resolve to a login/id first (the "one rule" above).
- **`--dry-run` on a `--user` command shows the lookup, not the write** — it stops at the
  first JSON-2 call. See the dry-run section.
- **`--mine` needs a login in the profile.** This profile has `login = admin`, so `--mine`
  works; a profile saved without a login errors and you must use `--user` instead.
- **No DB header here.** The profile has no `db` set (single-db host), so requests omit
  `X-Odoo-Database`. Multi-db hosts need `db` in the profile or `ODOO_DB`.

## Troubleshooting

- `No Odoo profile configured` / `No API key for profile` → not logged in. Run
  `uv run oc login` (interactive) or set `ODOO_URL`/`ODOO_API_KEY` env vars. (Per this
  skill's premise, it *is* logged in — `uv run oc profiles` confirms.)
- `Profile 'X' not found` → you passed `-p X` with no such profile; run `uv run oc profiles`
  to see configured names.
- Ambiguous-user exit code 1 → re-run with the login or numeric id shown in the error's
  candidate list.
