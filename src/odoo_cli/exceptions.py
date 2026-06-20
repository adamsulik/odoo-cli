"""Exception hierarchy for the Odoo CLI.

These are transport/SDK-level errors raised by the core (``client``/``resources``)
and translated into clean, user-facing messages by the CLI layer.
"""

from __future__ import annotations


class OdooError(Exception):
    """Base class for all Odoo CLI errors."""


class ConfigError(OdooError):
    """Raised when configuration is missing or malformed."""


class AuthError(OdooError):
    """Raised when authentication fails or no API key is available."""


class NotFoundError(OdooError):
    """Raised when a requested record (or a name lookup) yields nothing."""


class AmbiguousMatchError(OdooError):
    """Raised when a name/login lookup matches more than one record.

    Carries the candidate records so the CLI can show the user how to disambiguate.
    """

    def __init__(self, message: str, candidates: list[dict[str, object]]) -> None:
        super().__init__(message)
        self.candidates = candidates


class DryRun(OdooError):
    """Control-flow signal: a request was rendered in --dry-run mode and not sent.

    Raised by :class:`~odoo_cli.client.OdooClient` and caught at the CLI boundary to
    exit cleanly (status 0) without producing command output.
    """
