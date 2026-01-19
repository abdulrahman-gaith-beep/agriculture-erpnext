# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class Crop(Document):
	"""
	Crop DocType stores comprehensive information about crops including:
	- Basic identification (name, scientific name, code)
	- Growth characteristics (days to maturity, yield)
	- Climate requirements (temperature, humidity)
	- Water and soil requirements
	- Spacing and planting details
	- Varieties and growth stages
	- Associated pests and diseases
	"""

	def validate(self):
		self.validate_crop_tasks()
		self.validate_climate_requirements()
		self.validate_soil_requirements()
		self.calculate_period_from_stages()

	def validate_crop_tasks(self):
		if not self.agriculture_task:
			return

		for task in self.agriculture_task:
			if task.start_day > task.end_day:
				frappe.throw(_("Start day is greater than end day in task '{0}'").format(task.task_name))

		# Verify that the crop period is correct
		max_crop_period = max([task.end_day for task in self.agriculture_task])
		self.period = max(self.period or 0, max_crop_period)

		# Sort the crop tasks based on start days,
		# maintaining the order for same-day tasks
		self.agriculture_task.sort(key=lambda task: task.start_day)

	def validate_climate_requirements(self):
		"""Validate temperature and humidity ranges."""
		if self.optimal_temp_min and self.optimal_temp_max:
			if self.optimal_temp_min > self.optimal_temp_max:
				frappe.throw(_("Minimum temperature cannot be greater than maximum temperature"))

		if self.optimal_humidity_min and self.optimal_humidity_max:
			if self.optimal_humidity_min > self.optimal_humidity_max:
				frappe.throw(_("Minimum humidity cannot be greater than maximum humidity"))

	def validate_soil_requirements(self):
		"""Validate soil pH range."""
		if self.ph_min and self.ph_max:
			if self.ph_min > self.ph_max:
				frappe.throw(_("Minimum pH cannot be greater than maximum pH"))
			if self.ph_min < 0 or self.ph_max > 14:
				frappe.throw(_("pH values must be between 0 and 14"))

	def calculate_period_from_stages(self):
		"""Calculate total crop period from growth stages if defined."""
		if self.growth_stages:
			total_days = 0
			for stage in self.growth_stages:
				if stage.days_from_planting and stage.duration_days:
					end_day = stage.days_from_planting + stage.duration_days
					total_days = max(total_days, end_day)
			if total_days > 0:
				self.period = max(self.period or 0, total_days)

	@frappe.whitelist()
	def get_growth_stage_at_day(self, day):
		"""Get the growth stage for a specific day after planting."""
		if not self.growth_stages:
			return None

		for stage in sorted(self.growth_stages, key=lambda s: s.stage_number):
			if stage.days_from_planting and stage.duration_days:
				stage_end = stage.days_from_planting + stage.duration_days
				if stage.days_from_planting <= day < stage_end:
					return stage.stage_name
		return None

	@frappe.whitelist()
	def get_current_stage_requirements(self, day):
		"""Get water and nutrient requirements for a specific day."""
		if not self.growth_stages:
			return {"water": self.water_requirement, "nutrient": "Medium"}

		for stage in sorted(self.growth_stages, key=lambda s: s.stage_number):
			if stage.days_from_planting and stage.duration_days:
				stage_end = stage.days_from_planting + stage.duration_days
				if stage.days_from_planting <= day < stage_end:
					return {
						"stage": stage.stage_name,
						"water": stage.water_requirement or self.water_requirement,
						"nutrient": stage.nutrient_requirement or "Medium",
						"observations": stage.critical_observations
					}
		return {"water": self.water_requirement, "nutrient": "Medium"}

	@frappe.whitelist()
	def is_climate_suitable(self, temperature=None, humidity=None):
		"""Check if given climate conditions are suitable for this crop."""
		result = {"suitable": True, "warnings": []}

		if temperature is not None:
			if self.optimal_temp_min and temperature < self.optimal_temp_min:
				result["suitable"] = False
				result["warnings"].append(
					_("Temperature {0}°C is below minimum {1}°C").format(temperature, self.optimal_temp_min)
				)
			if self.optimal_temp_max and temperature > self.optimal_temp_max:
				result["suitable"] = False
				result["warnings"].append(
					_("Temperature {0}°C is above maximum {1}°C").format(temperature, self.optimal_temp_max)
				)

		if humidity is not None:
			if self.optimal_humidity_min and humidity < self.optimal_humidity_min:
				result["warnings"].append(
					_("Humidity {0}% is below optimal {1}%").format(humidity, self.optimal_humidity_min)
				)
			if self.optimal_humidity_max and humidity > self.optimal_humidity_max:
				result["warnings"].append(
					_("Humidity {0}% is above optimal {1}%").format(humidity, self.optimal_humidity_max)
				)

		return result


@frappe.whitelist()
def get_item_details(item_code):
	item = frappe.get_doc('Item', item_code)
	return {"uom": item.stock_uom, "rate": item.valuation_rate}


@frappe.whitelist()
def get_crops_by_category(category):
	"""Get all crops in a specific category."""
	return frappe.get_all(
		"Crop",
		filters={"category": category},
		fields=["name", "crop_name", "type", "days_to_maturity", "water_requirement"]
	)


@frappe.whitelist()
def get_crops_suitable_for_climate(temperature, humidity=None, climate_zone=None):
	"""Find crops suitable for given climate conditions."""
	filters = {}

	if climate_zone:
		filters["climate_zones"] = ["in", [climate_zone, "Multiple Zones"]]

	crops = frappe.get_all(
		"Crop",
		filters=filters,
		fields=["name", "crop_name", "optimal_temp_min", "optimal_temp_max",
				"optimal_humidity_min", "optimal_humidity_max", "climate_zones"]
	)

	suitable_crops = []
	for crop in crops:
		is_suitable = True

		if crop.optimal_temp_min and temperature < crop.optimal_temp_min:
			is_suitable = False
		if crop.optimal_temp_max and temperature > crop.optimal_temp_max:
			is_suitable = False

		if humidity and is_suitable:
			if crop.optimal_humidity_min and humidity < crop.optimal_humidity_min:
				is_suitable = False
			if crop.optimal_humidity_max and humidity > crop.optimal_humidity_max:
				is_suitable = False

		if is_suitable:
			suitable_crops.append(crop)

	return suitable_crops
