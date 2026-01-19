# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today, add_days


class FarmEquipment(Document):
	"""
	Farm Equipment tracks agricultural machinery and tools including:
	- Purchase and warranty details
	- Operating hours and fuel consumption
	- Maintenance scheduling and history
	- Insurance information
	- Cost tracking
	"""

	def validate(self):
		self.validate_dates()
		self.check_service_due()
		self.calculate_totals()

	def validate_dates(self):
		"""Validate date fields."""
		if self.purchase_date and self.warranty_expiry:
			if getdate(self.warranty_expiry) < getdate(self.purchase_date):
				frappe.throw(_("Warranty expiry date cannot be before purchase date"))

		if self.is_insured and self.insurance_expiry:
			if getdate(self.insurance_expiry) < getdate(today()):
				frappe.msgprint(_("Insurance has expired"), indicator="orange", alert=True)

	def check_service_due(self):
		"""Check if service is due based on operating hours."""
		if self.current_hours and self.last_service_hours and self.service_interval_hours:
			hours_since_service = flt(self.current_hours) - flt(self.last_service_hours)
			if hours_since_service >= flt(self.service_interval_hours):
				if self.status == "Available":
					frappe.msgprint(
						_("Service is overdue. Equipment has {0} hours since last service.").format(
							hours_since_service
						),
						indicator="red",
						alert=True
					)

	def calculate_totals(self):
		"""Calculate total fuel consumed and operating costs from maintenance logs."""
		total_fuel = 0
		total_cost = 0

		for log in self.maintenance_logs:
			if log.fuel_used:
				total_fuel += flt(log.fuel_used)
			if log.cost:
				total_cost += flt(log.cost)

		self.total_fuel_consumed = total_fuel
		self.total_operating_cost = total_cost

	@frappe.whitelist()
	def log_usage(self, hours_used, fuel_used=None, operator=None, notes=None):
		"""Log equipment usage and update operating hours."""
		self.current_hours = flt(self.current_hours) + flt(hours_used)

		self.append("maintenance_logs", {
			"log_type": "Usage",
			"log_date": today(),
			"hours_at_log": self.current_hours,
			"fuel_used": fuel_used,
			"performed_by": operator,
			"notes": notes
		})

		self.save()
		return self.current_hours

	@frappe.whitelist()
	def log_maintenance(self, maintenance_type, description, cost=None, performed_by=None):
		"""Log maintenance activity."""
		self.last_service_hours = self.current_hours

		self.append("maintenance_logs", {
			"log_type": "Maintenance",
			"maintenance_type": maintenance_type,
			"log_date": today(),
			"hours_at_log": self.current_hours,
			"description": description,
			"cost": cost,
			"performed_by": performed_by
		})

		if self.service_interval_hours:
			# Estimate next service date based on average daily usage
			self.next_service_due = add_days(today(), 30)

		self.save()

	@frappe.whitelist()
	def update_status(self, new_status, reason=None):
		"""Update equipment status with logging."""
		old_status = self.status
		self.status = new_status

		self.append("maintenance_logs", {
			"log_type": "Status Change",
			"log_date": today(),
			"hours_at_log": self.current_hours,
			"description": _("Status changed from {0} to {1}").format(old_status, new_status),
			"notes": reason
		})

		self.save()

	@frappe.whitelist()
	def get_usage_summary(self, from_date=None, to_date=None):
		"""Get usage summary for a period."""
		logs = self.maintenance_logs or []

		if from_date:
			logs = [l for l in logs if getdate(l.log_date) >= getdate(from_date)]
		if to_date:
			logs = [l for l in logs if getdate(l.log_date) <= getdate(to_date)]

		usage_logs = [l for l in logs if l.log_type == "Usage"]
		maintenance_logs = [l for l in logs if l.log_type == "Maintenance"]

		return {
			"total_usage_entries": len(usage_logs),
			"total_fuel_used": sum(flt(l.fuel_used) for l in usage_logs),
			"total_maintenance_entries": len(maintenance_logs),
			"total_maintenance_cost": sum(flt(l.cost) for l in maintenance_logs)
		}


@frappe.whitelist()
def get_equipment_due_for_service():
	"""Get all equipment due for service."""
	equipment_list = frappe.get_all(
		"Farm Equipment",
		filters={"status": ["not in", ["Out of Service", "Retired"]]},
		fields=["name", "equipment_name", "equipment_type", "current_hours",
				"last_service_hours", "service_interval_hours", "next_service_due"]
	)

	due_for_service = []
	for eq in equipment_list:
		if eq.current_hours and eq.last_service_hours and eq.service_interval_hours:
			hours_since_service = flt(eq.current_hours) - flt(eq.last_service_hours)
			if hours_since_service >= flt(eq.service_interval_hours) * 0.9:  # 90% of interval
				eq["hours_since_service"] = hours_since_service
				eq["overdue"] = hours_since_service >= flt(eq.service_interval_hours)
				due_for_service.append(eq)

	return due_for_service


@frappe.whitelist()
def get_equipment_by_farm(farm):
	"""Get all equipment assigned to a farm."""
	return frappe.get_all(
		"Farm Equipment",
		filters={"farm": farm, "status": ["!=", "Retired"]},
		fields=["name", "equipment_name", "equipment_type", "status",
				"current_hours", "fuel_type", "horsepower"]
	)
