# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_hours


class LaborActivity(Document):
	"""
	Labor Activity tracks farm worker tasks including:
	- Activity type and assignment
	- Worker attendance and hours
	- Cost calculation (regular and overtime)
	- Work output measurement
	- Quality assessment
	"""

	def validate(self):
		self.calculate_time()
		self.calculate_workers()
		self.calculate_costs()

	def calculate_time(self):
		"""Calculate total and actual working hours."""
		if self.start_time and self.end_time:
			# Calculate total hours
			self.total_hours = time_diff_in_hours(self.end_time, self.start_time)

			# Calculate actual working hours (excluding breaks)
			break_hours = flt(self.break_duration_minutes) / 60
			self.actual_working_hours = max(0, flt(self.total_hours) - break_hours)

	def calculate_workers(self):
		"""Count total workers."""
		self.total_workers = len(self.workers) if self.workers else 0

	def calculate_costs(self):
		"""Calculate labor costs."""
		total_worker_hours = 0
		total_overtime = 0

		for worker in self.workers or []:
			worker_hours = flt(worker.hours_worked) or flt(self.actual_working_hours)
			total_worker_hours += worker_hours
			total_overtime += flt(worker.overtime_hours)

		# If no individual hours, use activity hours * workers
		if total_worker_hours == 0 and self.actual_working_hours:
			total_worker_hours = flt(self.actual_working_hours) * flt(self.total_workers)
			total_overtime = flt(self.overtime_hours) * flt(self.total_workers)

		# Calculate regular cost
		if self.hourly_rate:
			self.regular_cost = flt(self.hourly_rate) * total_worker_hours

		# Calculate overtime cost
		if self.overtime_rate and total_overtime:
			self.overtime_cost = flt(self.overtime_rate) * total_overtime
		elif self.hourly_rate and total_overtime:
			# Default overtime at 1.5x regular rate
			self.overtime_cost = flt(self.hourly_rate) * 1.5 * total_overtime

		# Calculate total cost
		self.total_cost = (
			flt(self.regular_cost) +
			flt(self.overtime_cost) +
			flt(self.other_costs)
		)

	def on_submit(self):
		"""Actions on submission."""
		self.update_crop_cycle_costs()

	def update_crop_cycle_costs(self):
		"""Update crop cycle with labor costs."""
		if self.crop_cycle and self.total_cost:
			crop_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
			if hasattr(crop_cycle, "labor_cost"):
				crop_cycle.labor_cost = flt(crop_cycle.labor_cost) + flt(self.total_cost)
				crop_cycle.save(ignore_permissions=True)


@frappe.whitelist()
def get_labor_summary(farm=None, crop_cycle=None, from_date=None, to_date=None):
	"""Get labor activity summary for reporting."""
	filters = {"docstatus": 1}

	if farm:
		filters["farm"] = farm
	if crop_cycle:
		filters["crop_cycle"] = crop_cycle
	if from_date:
		filters["activity_date"] = [">=", from_date]
	if to_date:
		if "activity_date" in filters:
			filters["activity_date"] = ["between", [from_date, to_date]]
		else:
			filters["activity_date"] = ["<=", to_date]

	activities = frappe.get_all(
		"Labor Activity",
		filters=filters,
		fields=[
			"name", "activity_date", "activity_type", "total_workers",
			"actual_working_hours", "total_cost", "area_covered"
		]
	)

	# Summarize by activity type
	by_type = {}
	for act in activities:
		atype = act.activity_type or "Other"
		if atype not in by_type:
			by_type[atype] = {
				"count": 0,
				"total_hours": 0,
				"total_workers": 0,
				"total_cost": 0,
				"total_area": 0
			}
		by_type[atype]["count"] += 1
		by_type[atype]["total_hours"] += flt(act.actual_working_hours)
		by_type[atype]["total_workers"] += flt(act.total_workers)
		by_type[atype]["total_cost"] += flt(act.total_cost)
		by_type[atype]["total_area"] += flt(act.area_covered)

	return {
		"total_activities": len(activities),
		"total_cost": sum(flt(a.total_cost) for a in activities),
		"total_hours": sum(flt(a.actual_working_hours) for a in activities),
		"total_area_covered": sum(flt(a.area_covered) for a in activities),
		"by_type": by_type,
		"activities": activities
	}


@frappe.whitelist()
def get_activities_for_date(activity_date, farm=None):
	"""Get all activities for a specific date."""
	filters = {"activity_date": activity_date}
	if farm:
		filters["farm"] = farm

	return frappe.get_all(
		"Labor Activity",
		filters=filters,
		fields=[
			"name", "activity_type", "status", "farm", "crop_cycle",
			"total_workers", "start_time", "end_time", "total_cost"
		],
		order_by="start_time asc"
	)
