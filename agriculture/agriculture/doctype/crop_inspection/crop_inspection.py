# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, add_days


class CropInspection(Document):
	"""
	Crop Inspection tracks field monitoring activities including:
	- Crop health assessments
	- Pest and disease observations
	- Soil and irrigation conditions
	- Weather documentation
	- Recommendations and follow-up actions
	"""

	def validate(self):
		self.validate_dates()
		self.set_title()
		self.update_status_based_on_findings()

	def set_title(self):
		"""Auto-generate title if not set."""
		if not self.title:
			parts = []
			if self.inspection_type:
				parts.append(self.inspection_type)
			if self.crop:
				parts.append(self.crop)
			if self.farm:
				parts.append(self.farm)
			if self.inspection_date:
				parts.append(str(self.inspection_date))
			self.title = " - ".join(parts) if parts else "Crop Inspection"

	def validate_dates(self):
		"""Validate inspection and follow-up dates."""
		if self.inspection_date and getdate(self.inspection_date) > getdate(today()):
			frappe.throw(_("Inspection date cannot be in the future"))

		if self.follow_up_required and self.follow_up_date:
			if getdate(self.follow_up_date) <= getdate(self.inspection_date):
				frappe.throw(_("Follow-up date must be after inspection date"))

	def update_status_based_on_findings(self):
		"""Update status based on inspection findings."""
		if self.status == "Draft":
			return

		# Set to Action Required if immediate action needed or high severity issues
		if self.immediate_action_required:
			self.status = "Action Required"
		elif self.pest_severity in ["High", "Severe"] or self.disease_severity in ["High", "Severe"]:
			self.status = "Action Required"
		elif self.vigor_rating in ["Poor", "Critical"]:
			self.status = "Action Required"

	def on_submit(self):
		"""Actions on submission."""
		self.create_follow_up_todo()
		self.update_crop_cycle_health()

	def create_follow_up_todo(self):
		"""Create a ToDo for follow-up if required."""
		if self.follow_up_required and self.follow_up_date:
			todo = frappe.new_doc("ToDo")
			todo.description = _("Follow-up inspection required for {0}").format(self.name)
			todo.reference_type = "Crop Inspection"
			todo.reference_name = self.name
			todo.date = self.follow_up_date
			if self.follow_up_assigned_to:
				todo.allocated_to = self.follow_up_assigned_to
			todo.insert(ignore_permissions=True)

	def update_crop_cycle_health(self):
		"""Update the linked crop cycle with latest health status."""
		if self.crop_cycle:
			crop_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
			if hasattr(crop_cycle, "last_inspection_date"):
				crop_cycle.last_inspection_date = self.inspection_date
			if hasattr(crop_cycle, "last_health_rating"):
				crop_cycle.last_health_rating = self.overall_health_rating
			crop_cycle.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_follow_up_inspection(self):
		"""Create a new inspection as a follow-up to this one."""
		new_inspection = frappe.copy_doc(self)
		new_inspection.inspection_date = self.follow_up_date or add_days(today(), 7)
		new_inspection.status = "Draft"
		new_inspection.title = None  # Will be auto-generated
		new_inspection.findings = None
		new_inspection.recommendations = None
		new_inspection.priority_actions = []
		new_inspection.follow_up_required = 0
		new_inspection.follow_up_date = None
		new_inspection.follow_up_assigned_to = None
		new_inspection.photos = None
		new_inspection.insert()

		return new_inspection.name

	@frappe.whitelist()
	def get_historical_data(self):
		"""Get historical inspection data for the same crop cycle or farm."""
		filters = {}
		if self.crop_cycle:
			filters["crop_cycle"] = self.crop_cycle
		elif self.farm:
			filters["farm"] = self.farm
		else:
			return []

		filters["name"] = ["!=", self.name]
		filters["docstatus"] = ["!=", 2]

		inspections = frappe.get_all(
			"Crop Inspection",
			filters=filters,
			fields=[
				"name", "inspection_date", "inspection_type", "status",
				"overall_health_rating", "pest_severity", "disease_severity",
				"vigor_rating", "growth_stage"
			],
			order_by="inspection_date desc",
			limit=10
		)

		return inspections


@frappe.whitelist()
def get_inspection_summary(crop_cycle=None, farm=None, from_date=None, to_date=None):
	"""Get summary of inspections for reporting."""
	filters = {"docstatus": ["!=", 2]}

	if crop_cycle:
		filters["crop_cycle"] = crop_cycle
	if farm:
		filters["farm"] = farm
	if from_date:
		filters["inspection_date"] = [">=", from_date]
	if to_date:
		if "inspection_date" in filters:
			filters["inspection_date"] = ["between", [from_date, to_date]]
		else:
			filters["inspection_date"] = ["<=", to_date]

	inspections = frappe.get_all(
		"Crop Inspection",
		filters=filters,
		fields=[
			"name", "inspection_date", "inspection_type", "status",
			"overall_health_rating", "pest_severity", "disease_severity",
			"immediate_action_required"
		]
	)

	summary = {
		"total_inspections": len(inspections),
		"action_required": sum(1 for i in inspections if i.status == "Action Required"),
		"pest_issues": sum(1 for i in inspections if i.pest_severity in ["High", "Severe"]),
		"disease_issues": sum(1 for i in inspections if i.disease_severity in ["High", "Severe"]),
		"immediate_actions": sum(1 for i in inspections if i.immediate_action_required),
		"inspections": inspections
	}

	return summary


@frappe.whitelist()
def get_pending_follow_ups(assigned_to=None):
	"""Get all pending follow-up inspections."""
	filters = {
		"follow_up_required": 1,
		"follow_up_date": ["<=", today()],
		"status": ["!=", "Completed"],
		"docstatus": ["!=", 2]
	}

	if assigned_to:
		filters["follow_up_assigned_to"] = assigned_to

	return frappe.get_all(
		"Crop Inspection",
		filters=filters,
		fields=[
			"name", "title", "crop_cycle", "farm", "crop",
			"follow_up_date", "follow_up_assigned_to",
			"pest_severity", "disease_severity", "immediate_action_required"
		],
		order_by="follow_up_date asc"
	)
