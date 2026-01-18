# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class HarvestRecord(Document):
	"""
	Harvest Record tracks the yield and quality of harvested crops.

	Links to Crop Cycle for complete traceability from planting to harvest.
	Calculates yield percentages and financial metrics automatically.
	"""

	def validate(self):
		self.validate_quantities()
		self.calculate_yield_percentage()
		self.calculate_financial_values()
		self.set_title()

	def set_title(self):
		"""Auto-generate title if not set."""
		if not self.title:
			crop_name = self.crop or "Unknown Crop"
			self.title = f"{crop_name} - {self.harvest_date}"

	def validate_quantities(self):
		"""Validate harvest quantities."""
		if self.harvested_quantity < 0:
			frappe.throw(_("Harvested quantity cannot be negative"))

		if self.quality_rejected and self.quality_rejected > self.harvested_quantity:
			frappe.throw(_("Rejected quantity cannot exceed harvested quantity"))

		if self.expected_quantity and self.expected_quantity < 0:
			frappe.throw(_("Expected quantity cannot be negative"))

	def calculate_yield_percentage(self):
		"""Calculate actual yield as percentage of expected."""
		if self.expected_quantity and self.expected_quantity > 0:
			self.yield_percentage = flt(
				(self.harvested_quantity / self.expected_quantity) * 100,
				precision=2
			)
		else:
			self.yield_percentage = 0

	def calculate_financial_values(self):
		"""Calculate total and net values."""
		# Calculate total value from unit price
		if self.unit_price and self.harvested_quantity:
			# Subtract rejected quantity for saleable value
			saleable_qty = self.harvested_quantity - flt(self.quality_rejected)
			self.total_value = flt(self.unit_price * saleable_qty, precision=2)

		# Calculate estimated market value (same as total if unit price exists)
		if self.total_value:
			self.estimated_value = self.total_value

		# Calculate net value (total - costs)
		if self.total_value:
			total_costs = flt(self.cost_of_harvest) + flt(self.labor_cost)
			self.net_value = flt(self.total_value - total_costs, precision=2)

	def on_submit(self):
		"""Actions on submission."""
		self.status = "Completed"
		self.update_crop_cycle_yield()

	def on_cancel(self):
		"""Actions on cancellation."""
		self.status = "Cancelled"

	def update_crop_cycle_yield(self):
		"""Update the linked crop cycle with harvest data."""
		if self.crop_cycle:
			# Get all harvest records for this crop cycle
			total_harvested = frappe.db.sql("""
				SELECT SUM(harvested_quantity) as total
				FROM `tabHarvest Record`
				WHERE crop_cycle = %s
				AND docstatus = 1
			""", self.crop_cycle, as_dict=True)

			if total_harvested and total_harvested[0].total:
				frappe.db.set_value(
					"Crop Cycle",
					self.crop_cycle,
					"actual_yield",
					total_harvested[0].total
				)

	def before_insert(self):
		"""Set defaults from crop cycle."""
		if self.crop_cycle:
			cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
			if not self.crop:
				self.crop = cycle.crop
			if not self.farm and hasattr(cycle, 'farm'):
				self.farm = cycle.farm

	@frappe.whitelist()
	def get_crop_cycle_details(self):
		"""Fetch details from linked crop cycle."""
		if not self.crop_cycle:
			return {}

		cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
		return {
			"crop": cycle.crop,
			"start_date": cycle.start_date,
			"expected_yield": getattr(cycle, 'expected_yield', 0),
			"locations": [loc.location for loc in cycle.linked_location] if cycle.linked_location else []
		}


@frappe.whitelist()
def get_harvest_summary(crop_cycle=None, farm=None, from_date=None, to_date=None):
	"""Get harvest summary statistics."""
	filters = {"docstatus": 1}

	if crop_cycle:
		filters["crop_cycle"] = crop_cycle
	if farm:
		filters["farm"] = farm

	date_conditions = ""
	if from_date:
		date_conditions += f" AND harvest_date >= '{from_date}'"
	if to_date:
		date_conditions += f" AND harvest_date <= '{to_date}'"

	query = f"""
		SELECT
			crop,
			COUNT(*) as harvest_count,
			SUM(harvested_quantity) as total_quantity,
			SUM(total_value) as total_value,
			SUM(net_value) as net_value,
			AVG(yield_percentage) as avg_yield_pct
		FROM `tabHarvest Record`
		WHERE docstatus = 1
		{date_conditions}
		GROUP BY crop
		ORDER BY total_quantity DESC
	"""

	return frappe.db.sql(query, as_dict=True)
