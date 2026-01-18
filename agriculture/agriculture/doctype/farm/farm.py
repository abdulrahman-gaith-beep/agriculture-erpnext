# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Farm(Document):
	"""
	Farm DocType represents a farm or agricultural property.

	A farm can have multiple fields/plots, water sources, and irrigation systems.
	It tracks area, soil type, climate zone, and certifications.
	"""

	def validate(self):
		self.validate_areas()
		self.validate_coordinates()
		self.validate_certifications()
		self.calculate_area_totals()

	def validate_areas(self):
		"""Ensure area values are consistent."""
		if self.cultivable_area and self.total_area:
			if self.cultivable_area > self.total_area:
				frappe.throw(_("Cultivable area cannot exceed total area"))

		if self.irrigated_area and self.cultivable_area:
			if self.irrigated_area > self.cultivable_area:
				frappe.throw(_("Irrigated area cannot exceed cultivable area"))

		if self.non_cultivable_area and self.total_area:
			if self.non_cultivable_area > self.total_area:
				frappe.throw(_("Non-cultivable area cannot exceed total area"))

	def validate_coordinates(self):
		"""Validate GPS coordinates if provided."""
		if self.latitude:
			if self.latitude < -90 or self.latitude > 90:
				frappe.throw(_("Latitude must be between -90 and 90"))

		if self.longitude:
			if self.longitude < -180 or self.longitude > 180:
				frappe.throw(_("Longitude must be between -180 and 180"))

	def validate_certifications(self):
		"""Validate certification dates."""
		if self.is_organic_certified and self.organic_valid_until:
			if frappe.utils.getdate(self.organic_valid_until) < frappe.utils.getdate():
				frappe.msgprint(
					_("Organic certification has expired on {0}").format(self.organic_valid_until),
					indicator="orange",
					alert=True
				)

	def calculate_area_totals(self):
		"""Calculate total field area from child table."""
		if self.fields:
			total_field_area = sum(field.area or 0 for field in self.fields)
			if total_field_area > 0 and self.cultivable_area:
				if total_field_area > self.cultivable_area:
					frappe.msgprint(
						_("Sum of field areas ({0}) exceeds cultivable area ({1})").format(
							total_field_area, self.cultivable_area
						),
						indicator="orange"
					)

	def get_active_crop_cycles(self):
		"""Get all active crop cycles on this farm's fields."""
		if not self.fields:
			return []

		field_locations = [f.location for f in self.fields if f.location]
		if not field_locations:
			return []

		return frappe.get_all(
			"Crop Cycle",
			filters={
				"linked_location": ["in", field_locations]
			},
			fields=["name", "title", "crop", "start_date", "status"]
		)

	def get_soil_analyses(self, limit=10):
		"""Get recent soil analyses for this farm's location."""
		if not self.location:
			return []

		return frappe.get_all(
			"Soil Analysis",
			filters={"location": self.location},
			fields=["name", "collection_datetime", "result_datetime"],
			order_by="collection_datetime desc",
			limit=limit
		)

	@frappe.whitelist()
	def get_farm_summary(self):
		"""Get summary statistics for the farm."""
		summary = {
			"total_area": self.total_area,
			"cultivable_area": self.cultivable_area or 0,
			"irrigated_area": self.irrigated_area or 0,
			"field_count": len(self.fields) if self.fields else 0,
			"water_source_count": len(self.water_sources) if self.water_sources else 0,
			"is_organic": self.is_organic_certified,
			"active_crop_cycles": len(self.get_active_crop_cycles()),
		}
		return summary
