"""Connection profiles and credential resolution.

Profiles (host + database) live in a TOML file under the user config dir; secrets never
do. The API key is resolved from the ``ODOO_API_KEY`` environment variable first, then the
OS keyring. ``host``/``db`` can likewise be overridden by ``ODOO_URL``/``ODOO_DB``.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .exceptions import AuthError, ConfigError

KEYRING_SERVICE = "odoo-cli"
ENV_API_KEY = "ODOO_API_KEY"
ENV_URL = "ODOO_URL"
ENV_DB = "ODOO_DB"
ENV_PROFILE = "ODOO_PROFILE"


def config_dir() -> Path:
    """Return the config directory, honouring ``XDG_CONFIG_HOME``."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "odoo-cli"


def config_path() -> Path:
    return config_dir() / "config.toml"


@dataclass(frozen=True)
class Profile:
    """A resolved connection target. ``api_key`` is filled in only by :func:`resolve`.

    ``login`` is the API key owner's own login, captured at ``oc login`` time so that
    ``--mine`` filters can resolve "me" to a user id without a JSON-2 whoami call.
    """

    name: str
    host: str
    db: str | None = None
    login: str | None = None
    api_key: str | None = None


@dataclass
class ConfigFile:
    """In-memory view of ``config.toml``."""

    default: str | None
    profiles: dict[str, Profile]


def load_config() -> ConfigFile:
    """Load the TOML config file, returning an empty config if it does not exist."""
    path = config_path()
    if not path.exists():
        return ConfigFile(default=None, profiles={})
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Could not parse {path}: {exc}") from exc

    raw_profiles = data.get("profile", {})
    profiles: dict[str, Profile] = {}
    for name, body in raw_profiles.items():
        if "host" not in body:
            raise ConfigError(f"Profile '{name}' in {path} is missing required key 'host'.")
        profiles[name] = Profile(
            name=name, host=str(body["host"]), db=body.get("db"), login=body.get("login")
        )
    return ConfigFile(default=data.get("default"), profiles=profiles)


def _get_api_key(profile_name: str) -> str | None:
    """Resolve the API key: env var wins, then the OS keyring."""
    env = os.environ.get(ENV_API_KEY)
    if env:
        return env
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, profile_name)
    except Exception:
        # keyring backend may be unavailable (e.g. headless CI) — fall back to None.
        return None


def resolve(profile_name: str | None) -> Profile:
    """Resolve a fully-populated :class:`Profile` (including ``api_key``) for use.

    Resolution order for which profile: explicit arg → ``ODOO_PROFILE`` env → config default.
    Host/db/key can each be overridden by environment variables, which also makes the CLI
    usable with no config file at all (CI-friendly).
    """
    cfg = load_config()
    name = profile_name or os.environ.get(ENV_PROFILE) or cfg.default

    env_host = os.environ.get(ENV_URL)
    env_db = os.environ.get(ENV_DB)

    if name and name in cfg.profiles:
        base = cfg.profiles[name]
    elif name:
        raise ConfigError(
            f"Profile '{name}' not found in {config_path()}. Run `oc login --profile {name}`."
        )
    elif env_host:
        # No named profile, but env vars provide everything we need.
        base = Profile(name="env", host=env_host, db=env_db)
    else:
        raise ConfigError(
            "No Odoo profile configured. Run `oc login` or set ODOO_URL/ODOO_API_KEY."
        )

    host = (env_host or base.host).rstrip("/")
    db = env_db if env_db is not None else base.db
    api_key = _get_api_key(base.name)
    if not api_key:
        raise AuthError(
            f"No API key for profile '{base.name}'. "
            f"Run `oc login --profile {base.name}` or set {ENV_API_KEY}."
        )
    return Profile(name=base.name, host=host, db=db, login=base.login, api_key=api_key)


def save_profile(
    name: str, host: str, db: str | None, *, login: str | None = None, make_default: bool
) -> None:
    """Persist a profile (host/db/login) to the TOML config. Secrets are stored separately."""
    cfg = load_config()
    cfg.profiles[name] = Profile(name=name, host=host.rstrip("/"), db=db, login=login)
    if make_default or cfg.default is None:
        cfg.default = name

    lines: list[str] = []
    if cfg.default:
        lines.append(f'default = "{cfg.default}"')
        lines.append("")
    for pname, profile in cfg.profiles.items():
        lines.append(f"[profile.{pname}]")
        lines.append(f'host = "{profile.host}"')
        if profile.db:
            lines.append(f'db = "{profile.db}"')
        if profile.login:
            lines.append(f'login = "{profile.login}"')
        lines.append("")

    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def save_api_key(profile_name: str, api_key: str) -> None:
    """Store the API key in the OS keyring under the profile name."""
    import keyring

    keyring.set_password(KEYRING_SERVICE, profile_name, api_key)
