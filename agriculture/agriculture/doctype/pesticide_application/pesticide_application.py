# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days, add_to_date, now_datetime


class PesticideApplication(Document):
	"""
	Pesticide Application tracks pest control treatments including:
	- Target pest/disease information
	- Product details and quantities
	- Application method and weather conditions
	- Safety intervals (REI and PHI)
	- Effectiveness assessment
	- Compliance tracking
	"""

	def validate(self):
		self.validate_target()
		self.calculate_totals()
		self.calculate_safety_dates()
		self.check_weather_suitability()

	def validate_target(self):
		"""Validate target pest/disease based on target type."""
		if self.target_type == "Pest" and not self.target_pest:
			frappe.msgprint(_("Please specify the target pest"), indicator="orange")
		elif self.target_type == "Disease" and not self.target_disease:
			frappe.msgprint(_("Please specify the target disease"), indicator="orange")
		elif self.target_type == "Pest and Disease":
			if not self.target_pest and not self.target_disease:
				frappe.msgprint(_("Please specify at least one target pest or disease"), indicator="orange")

	def calculate_totals(self):
		"""Calculate total mixture volume and cost."""
		# Calculate total mixture volume
		if self.water_volume:
			self.total_mixture_volume = flt(self.water_volume) + flt(self.product_quantity_used)
		else:
			self.total_mixture_volume = flt(self.product_quantity_used)

		# Calculate total cost
		if self.cost_per_unit and self.product_quantity_used:
			self.total_cost = flt(self.cost_per_unit) * flt(self.product_quantity_used)

	def calculate_safety_dates(self):
		"""Calculate re-entry and safe harvest dates."""
		if self.application_date:
			# Calculate re-entry date/time
			if self.re_entry_interval_hours:
				self.re_entry_date = add_to_date(
					self.application_date,
					hours=self.re_entry_interval_hours
				)

			# Calculate safe harvest date
			if self.pre_harvest_interval_days:
				self.safe_harvest_date = add_days(
					getdate(self.application_date),
					self.pre_harvest_interval_days
				)

	def check_weather_suitability(self):
		"""Check if weather conditions are suitable for application."""
		warnings = []

		if self.wind_speed and flt(self.wind_speed) > 15:
			warnings.append(_("Wind speed is high ({0} km/h). Risk of spray drift.").format(self.wind_speed))
			self.weather_suitable = 0

		if self.temperature:
			if flt(self.temperature) > 35:
				warnings.append(_("Temperature is high ({0}°C). Product efficacy may be reduced.").format(self.temperature))
			elif flt(self.temperature) < 10:
				warnings.append(_("Temperature is low ({0}°C). Some products may be less effective.").format(self.temperature))

		if self.weather_conditions == "Light Rain":
			warnings.append(_("Rain may wash off the application"))
			self.weather_suitable = 0

		for warning in warnings:
			frappe.msgprint(warning, indicator="orange", alert=True)

	def on_submit(self):
		"""Actions on submission."""
		self.update_crop_cycle_costs()
		self.create_follow_up_reminder()

	def update_crop_cycle_costs(self):
		"""Update crop cycle with pesticide application costs."""
		if self.crop_cycle and self.total_cost:
			crop_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
			if hasattr(crop_cycle, "input_cost"):
				crop_cycle.input_cost = flt(crop_cycle.input_cost) + flt(self.total_cost)
				crop_cycle.save(ignore_permissions=True)

	def create_follow_up_reminder(self):
		"""Create a ToDo for follow-up if required."""
		if self.follow_up_required and self.follow_up_date:
			todo = frappe.new_doc("ToDo")
			todo.description = _("Follow-up pesticide application required for {0}").format(self.name)
			todo.reference_type = "Pesticide Application"
			todo.reference_name = self.name
			todo.date = self.follow_up_date
			todo.insert(ignore_permissions=True)

	@frappe.whitelist()
	def assess_effectiveness(self, rating, observations=None):
		"""Record effectiveness assessment."""
		self.effectiveness_rating = rating
		if observations:
			self.observations = observations

		if rating == "Not Effective" or rating == "Partially Effective":
			self.follow_up_required = 1
			if not self.follow_up_date:
				self.follow_up_date = add_days(getdate(self.application_date), 7)

		self.save()


@frappe.whitelist()
def get_applications_for_crop_cycle(crop_cycle):
	"""Get all pesticide applications for a crop cycle."""
	return frappe.get_all(
		"Pesticide Application",
		filters={"crop_cycle": crop_cycle, "docstatus": ["!=", 2]},
		fields=[
			"name", "application_date", "pesticide_type", "product_name",
			"target_type", "target_pest", "target_disease", "area_treated",
			"total_cost", "effectiveness_rating", "safe_harvest_date"
		],
		order_by="application_date desc"
	)


@frappe.whitelist()
def get_harvest_restrictions(crop_cycle=None, farm=None):
	"""Get active harvest restrictions due to pesticide applications."""
	filters = {
		"docstatus": 1,
		"safe_harvest_date": [">=", frappe.utils.today()]
	}

	if crop_cycle:
		filters["crop_cycle"] = crop_cycle
	if farm:
		filters["farm"] = farm

	return frappe.get_all(
		"Pesticide Application",
		filters=filters,
		fields=[
			"name", "application_date", "product_name", "crop_cycle",
			"farm", "safe_harvest_date", "pre_harvest_interval_days"
		],
		order_by="safe_harvest_date asc"
	)


@frappe.whitelist()
def get_pesticide_usage_summary(from_date=None, to_date=None, farm=None, crop=None):
	"""Get summary of pesticide usage for reporting."""
	filters = {"docstatus": 1}

	if from_date:
		filters["application_date"] = [">=", from_date]
	if to_date:
		if "application_date" in filters:
			filters["application_date"] = ["between", [from_date, to_date]]
		else:
			filters["application_date"] = ["<=", to_date]
	if farm:
		filters["farm"] = farm
	if crop:
		filters["crop"] = crop

	applications = frappe.get_all(
		"Pesticide Application",
		filters=filters,
		fields=[
			"pesticide_type", "product_name", "product_quantity_used",
			"area_treated", "total_cost", "effectiveness_rating"
		]
	)

	# Summarize by type
	by_type = {}
	for app in applications:
		ptype = app.pesticide_type or "Other"
		if ptype not in by_type:
			by_type[ptype] = {
				"count": 0,
				"total_quantity": 0,
				"total_area": 0,
				"total_cost": 0
			}
		by_type[ptype]["count"] += 1
		by_type[ptype]["total_quantity"] += flt(app.product_quantity_used)
		by_type[ptype]["total_area"] += flt(app.area_treated)
		by_type[ptype]["total_cost"] += flt(app.total_cost)

	return {
		"total_applications": len(applications),
		"total_cost": sum(flt(a.total_cost) for a in applications),
		"total_area_treated": sum(flt(a.area_treated) for a in applications),
		"by_type": by_type,
		"applications": applications
	}
