"""odoo-cli: a human-friendly CLI + importable SDK for the Odoo 19 External JSON-2 API."""

from .client import OdooClient
from .resources import CrmLead, ResUsers

__all__ = ["OdooClient", "CrmLead", "ResUsers"]
