# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Pest(Document):
	"""
	Pest DocType for managing pest information and control strategies.

	Separate from Disease DocType to handle:
	- Different pest types (insects, mites, rodents, etc.)
	- Favorable environmental conditions
	- Economic thresholds for treatment decisions
	- Integrated Pest Management (IPM) strategies
	"""

	def validate(self):
		self.validate_conditions()

	def validate_conditions(self):
		"""Validate temperature and humidity ranges."""
		if self.favorable_temperature_min and self.favorable_temperature_max:
			if self.favorable_temperature_min > self.favorable_temperature_max:
				frappe.throw(_("Minimum temperature cannot exceed maximum temperature"))

		if self.favorable_humidity_min and self.favorable_humidity_max:
			if self.favorable_humidity_min > self.favorable_humidity_max:
				frappe.throw(_("Minimum humidity cannot exceed maximum humidity"))

	def is_conditions_favorable(self, temperature=None, humidity=None):
		"""Check if current conditions are favorable for this pest."""
		favorable = True

		if temperature is not None:
			if self.favorable_temperature_min and temperature < self.favorable_temperature_min:
				favorable = False
			if self.favorable_temperature_max and temperature > self.favorable_temperature_max:
				favorable = False

		if humidity is not None:
			if self.favorable_humidity_min and humidity < self.favorable_humidity_min:
				favorable = False
			if self.favorable_humidity_max and humidity > self.favorable_humidity_max:
				favorable = False

		return favorable


@frappe.whitelist()
def check_pest_risk(location, crop=None):
	"""
	Check pest risk based on current weather conditions.

	Returns list of pests with high risk for the given location and crop.
	"""
	from agriculture.agriculture.doctype.irrigation_schedule.irrigation_schedule import get_latest_weather

	weather = get_latest_weather(location)
	if not weather:
		return []

	temperature = weather.get("Temperature Average") or weather.get("temperature")
	humidity = weather.get("Humidity") or weather.get("humidity")

	pests = frappe.get_all(
		"Pest",
		filters={"status": ["in", ["Active", "Seasonal"]]},
		fields=["name", "common_name", "pest_type", "severity_level",
				"favorable_temperature_min", "favorable_temperature_max",
				"favorable_humidity_min", "favorable_humidity_max"]
	)

	at_risk = []
	for pest in pests:
		pest_doc = frappe.get_doc("Pest", pest.name)
		if pest_doc.is_conditions_favorable(temperature, humidity):
			# Check if pest affects the given crop
			if crop:
				affected_crops = [c.crop for c in pest_doc.affected_crops] if pest_doc.affected_crops else []
				if crop in affected_crops or not affected_crops:
					at_risk.append({
						"pest": pest.name,
						"name": pest.common_name,
						"type": pest.pest_type,
						"severity": pest.severity_level
					})
			else:
				at_risk.append({
					"pest": pest.name,
					"name": pest.common_name,
					"type": pest.pest_type,
					"severity": pest.severity_level
				})

	return at_risk
