# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate


class FertilizerApplication(Document):
	"""
	Fertilizer Application tracks the application of inputs (fertilizers, pesticides, etc.)
	to crops. Essential for traceability, compliance, and organic certification.
	"""

	def validate(self):
		self.validate_quantities()
		self.calculate_application_rate()
		self.calculate_safe_harvest_date()
		self.calculate_costs()
		self.set_title()
		self.validate_organic_compliance()

	def set_title(self):
		"""Auto-generate title if not set."""
		if not self.title:
			input_name = self.fertilizer or self.application_type
			self.title = f"{input_name} - {self.application_date}"

	def validate_quantities(self):
		"""Validate application quantities."""
		if self.quantity_applied <= 0:
			frappe.throw(_("Quantity applied must be greater than zero"))

		if self.coverage_area and self.coverage_area < 0:
			frappe.throw(_("Coverage area cannot be negative"))

	def calculate_application_rate(self):
		"""Calculate application rate (quantity per unit area)."""
		if self.quantity_applied and self.coverage_area and self.coverage_area > 0:
			rate = flt(self.quantity_applied / self.coverage_area, precision=3)
			self.application_rate = f"{rate} {self.quantity_uom or ''} per {self.area_uom or 'unit'}"

	def calculate_safe_harvest_date(self):
		"""Calculate safe harvest date based on withholding period."""
		if self.withholding_period_days and self.application_date:
			self.safe_harvest_date = add_days(
				getdate(self.application_date),
				self.withholding_period_days
			)

	def calculate_costs(self):
		"""Calculate total cost."""
		if self.unit_cost and self.quantity_applied:
			self.total_cost = flt(self.unit_cost * self.quantity_applied, precision=2)

	def validate_organic_compliance(self):
		"""Warn if non-organic input applied to organic-certified farm."""
		if self.farm and not self.is_organic_approved:
			farm = frappe.get_doc("Farm", self.farm)
			if farm.is_organic_certified:
				frappe.msgprint(
					_("Warning: This input is not organic approved but is being applied to an organic certified farm ({0})").format(self.farm),
					indicator="orange",
					alert=True
				)

	def on_submit(self):
		"""Actions on submission."""
		self.status = "Completed"
		self.create_stock_entry()
		self.update_crop_cycle_costs()

	def on_cancel(self):
		"""Actions on cancellation."""
		self.status = "Cancelled"

	def create_stock_entry(self):
		"""Create stock entry for inventory deduction if item is linked."""
		if self.item and frappe.db.exists("Item", self.item):
			# Check if stock tracking is enabled for this item
			item = frappe.get_doc("Item", self.item)
			if item.is_stock_item:
				try:
					# Create Material Issue stock entry
					stock_entry = frappe.get_doc({
						"doctype": "Stock Entry",
						"stock_entry_type": "Material Issue",
						"posting_date": self.application_date,
						"items": [{
							"item_code": self.item,
							"qty": self.quantity_applied,
							"s_warehouse": frappe.db.get_single_value("Stock Settings", "default_warehouse")
						}]
					})
					stock_entry.insert(ignore_permissions=True)
					frappe.msgprint(_("Stock Entry {0} created for inventory deduction").format(stock_entry.name))
				except Exception as e:
					frappe.log_error(f"Failed to create stock entry: {str(e)}")

	def update_crop_cycle_costs(self):
		"""Update crop cycle with application costs."""
		if self.crop_cycle:
			total_cost = flt(self.total_cost) + flt(self.labor_cost) + flt(self.equipment_cost)
			if total_cost > 0:
				# Accumulate input costs on crop cycle
				current_cost = frappe.db.get_value("Crop Cycle", self.crop_cycle, "input_cost") or 0
				frappe.db.set_value(
					"Crop Cycle",
					self.crop_cycle,
					"input_cost",
					flt(current_cost) + total_cost
				)

	@frappe.whitelist()
	def get_fertilizer_details(self):
		"""Fetch details from linked fertilizer."""
		if not self.fertilizer:
			return {}

		fert = frappe.get_doc("Fertilizer", self.fertilizer)
		return {
			"item": fert.item if hasattr(fert, 'item') else None,
			"contents": [{"content": c.content, "value": c.value} for c in fert.fertilizer_contents] if fert.fertilizer_contents else []
		}


@frappe.whitelist()
def get_application_history(crop_cycle=None, farm=None, application_type=None, from_date=None, to_date=None):
	"""Get fertilizer application history with filters."""
	filters = {"docstatus": 1}

	if crop_cycle:
		filters["crop_cycle"] = crop_cycle
	if farm:
		filters["farm"] = farm
	if application_type:
		filters["application_type"] = application_type

	date_conditions = []
	if from_date:
		date_conditions.append(["application_date", ">=", from_date])
	if to_date:
		date_conditions.append(["application_date", "<=", to_date])

	return frappe.get_all(
		"Fertilizer Application",
		filters=filters + date_conditions if date_conditions else filters,
		fields=[
			"name", "title", "application_type", "application_date",
			"fertilizer", "quantity_applied", "quantity_uom",
			"coverage_area", "total_cost", "is_organic_approved"
		],
		order_by="application_date desc"
	)
