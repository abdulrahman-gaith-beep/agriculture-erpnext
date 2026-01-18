# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AgricultureSettings(Document):
	"""
	Agriculture Settings is a single DocType that stores module-wide configuration.

	Settings include:
	- Default UOMs for area, yield, spacing
	- Automation options (project/task creation)
	- Analysis lab defaults and reminder periods
	- Notification settings
	- Financial tracking options
	- Compliance and traceability settings
	- External API integrations
	"""
	pass


def get_agriculture_settings():
	"""Get the Agriculture Settings document."""
	return frappe.get_single("Agriculture Settings")


def get_default_uom(uom_type):
	"""Get default UOM based on type."""
	settings = get_agriculture_settings()
	uom_map = {
		"area": settings.default_area_uom,
		"yield": settings.default_yield_uom,
		"spacing": settings.default_spacing_uom
	}
	return uom_map.get(uom_type, "Unit")


def is_organic_tracking_enabled():
	"""Check if organic certification tracking is enabled."""
	settings = get_agriculture_settings()
	return settings.enable_organic_tracking


def is_traceability_enabled():
	"""Check if full traceability is enabled."""
	settings = get_agriculture_settings()
	return settings.enable_traceability


def get_traceability_prefix():
	"""Get the traceability prefix for batch numbering."""
	settings = get_agriculture_settings()
	return settings.traceability_prefix or "TRACE"
