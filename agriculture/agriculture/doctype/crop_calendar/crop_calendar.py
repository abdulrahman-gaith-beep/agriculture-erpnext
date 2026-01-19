# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, date_diff


class CropCalendar(Document):
	"""
	Crop Calendar for seasonal planning including:
	- Growing period definition
	- Planned crops with timing and area
	- Resource and cost estimation
	- Revenue and profit projections
	"""

	def validate(self):
		self.validate_dates()
		self.calculate_totals()
		self.calculate_projections()

	def validate_dates(self):
		"""Validate season dates."""
		if self.season_start and self.season_end:
			if getdate(self.season_end) <= getdate(self.season_start):
				frappe.throw(_("Season end date must be after start date"))

			# Calculate season duration
			duration = date_diff(self.season_end, self.season_start)
			if duration < 30:
				frappe.msgprint(_("Season duration is only {0} days").format(duration), indicator="orange")

	def calculate_totals(self):
		"""Calculate total planned area and estimated costs."""
		total_area = 0
		for item in self.planned_crops:
			total_area += flt(item.planned_area)

		self.total_planned_area = total_area

		# Calculate total estimated cost
		self.total_estimated_cost = (
			flt(self.estimated_seed_cost) +
			flt(self.estimated_fertilizer_cost) +
			flt(self.estimated_labor_cost) +
			flt(self.estimated_equipment_cost)
		)

	def calculate_projections(self):
		"""Calculate yield, revenue, and profit projections."""
		total_yield = 0
		total_revenue = 0

		for item in self.planned_crops:
			if item.expected_yield:
				total_yield += flt(item.expected_yield)
			if item.expected_revenue:
				total_revenue += flt(item.expected_revenue)

		self.estimated_total_yield = total_yield
		self.estimated_revenue = total_revenue

		# Calculate profit and ROI
		if self.total_estimated_cost:
			self.estimated_profit = flt(self.estimated_revenue) - flt(self.total_estimated_cost)
			self.roi_percentage = (flt(self.estimated_profit) / flt(self.total_estimated_cost)) * 100
		else:
			self.estimated_profit = flt(self.estimated_revenue)
			self.roi_percentage = 0

	@frappe.whitelist()
	def create_crop_cycles(self):
		"""Create crop cycles from the planned crops."""
		created_cycles = []

		for item in self.planned_crops:
			if item.crop and item.planned_start_date:
				crop_cycle = frappe.new_doc("Crop Cycle")
				crop_cycle.title = f"{item.crop} - {self.title}"
				crop_cycle.crop = item.crop
				crop_cycle.farm = self.farm
				crop_cycle.start_date = item.planned_start_date
				crop_cycle.end_date = item.planned_end_date
				crop_cycle.status = "Planning"

				if hasattr(crop_cycle, "planted_area"):
					crop_cycle.planted_area = item.planned_area
				if hasattr(crop_cycle, "expected_yield"):
					crop_cycle.expected_yield = item.expected_yield

				crop_cycle.insert()
				created_cycles.append(crop_cycle.name)

				# Update the calendar item with the created cycle
				item.crop_cycle = crop_cycle.name

		self.save()

		frappe.msgprint(
			_("Created {0} crop cycles").format(len(created_cycles)),
			indicator="green"
		)

		return created_cycles

	@frappe.whitelist()
	def update_status(self, new_status):
		"""Update calendar status."""
		self.status = new_status
		self.save()


@frappe.whitelist()
def get_calendars_for_farm(farm, year=None):
	"""Get all crop calendars for a farm."""
	filters = {"farm": farm}
	if year:
		filters["year"] = year

	return frappe.get_all(
		"Crop Calendar",
		filters=filters,
		fields=[
			"name", "title", "season", "year", "status",
			"season_start", "season_end", "total_planned_area",
			"total_estimated_cost", "estimated_profit"
		],
		order_by="year desc, season_start desc"
	)


@frappe.whitelist()
def get_planting_schedule(farm=None, from_date=None, to_date=None):
	"""Get planting schedule across all calendars."""
	filters = {"status": ["not in", ["Draft", "Cancelled"]]}

	if from_date:
		filters["season_start"] = [">=", from_date]
	if to_date:
		filters["season_end"] = ["<=", to_date]

	calendars = frappe.get_all(
		"Crop Calendar",
		filters=filters,
		fields=["name", "farm", "title", "season", "year"]
	)

	schedule = []
	for cal in calendars:
		if farm and cal.farm != farm:
			continue

		items = frappe.get_all(
			"Crop Calendar Item",
			filters={"parent": cal.name},
			fields=[
				"crop", "planned_area", "planned_start_date",
				"planned_end_date", "expected_yield", "priority"
			]
		)

		for item in items:
			item["calendar"] = cal.name
			item["farm"] = cal.farm
			item["season"] = cal.season
			schedule.append(item)

	# Sort by planned start date
	schedule.sort(key=lambda x: x.get("planned_start_date") or "9999-12-31")

	return schedule
