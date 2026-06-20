"""Importable, CLI-agnostic SDK: one class per Odoo model, built on :class:`OdooClient`."""

from .crm_lead import CrmLead
from .res_users import ResUsers

__all__ = ["CrmLead", "ResUsers"]
