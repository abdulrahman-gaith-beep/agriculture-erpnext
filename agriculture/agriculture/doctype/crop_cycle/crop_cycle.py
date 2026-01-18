# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import ast

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate


class CropCycle(Document):
	"""
	Crop Cycle manages the complete lifecycle of a crop from planting to harvest.

	Features:
	- Automatic project and task generation from crop template
	- Disease detection and treatment task creation
	- Financial tracking (costs, revenue, profit)
	- Yield tracking (expected vs actual)
	- Integration with Harvest Records and Fertilizer Applications
	"""

	def validate(self):
		self.set_missing_values()
		self.calculate_financials()
		self.calculate_yield_percentage()
		self.update_status_on_completion()

	def after_insert(self):
		self.create_crop_cycle_project()
		self.create_tasks_for_diseases()

	def on_update(self):
		self.create_tasks_for_diseases()

	def calculate_financials(self):
		"""Calculate total cost and profit."""
		self.total_cost = flt(self.input_cost) + flt(self.labor_cost) + \
						  flt(self.equipment_cost) + flt(self.other_cost)

		if self.revenue:
			self.profit = flt(self.revenue) - flt(self.total_cost)

	def calculate_yield_percentage(self):
		"""Calculate actual yield as percentage of expected."""
		if self.expected_yield and self.expected_yield > 0 and self.actual_yield:
			self.yield_percentage = flt(
				(self.actual_yield / self.expected_yield) * 100,
				precision=2
			)

	def update_status_on_completion(self):
		"""Auto-update status based on conditions."""
		if self.actual_end_date and self.status not in ["Completed", "Abandoned"]:
			if self.actual_yield and self.actual_yield > 0:
				self.status = "Completed"

	@frappe.whitelist()
	def calculate_from_records(self):
		"""Recalculate yield and revenue from linked Harvest Records."""
		# Get harvest totals
		harvest_data = frappe.db.sql("""
			SELECT
				SUM(harvested_quantity) as total_yield,
				SUM(total_value) as total_revenue
			FROM `tabHarvest Record`
			WHERE crop_cycle = %s AND docstatus = 1
		""", self.name, as_dict=True)

		if harvest_data and harvest_data[0]:
			self.actual_yield = flt(harvest_data[0].total_yield)
			self.revenue = flt(harvest_data[0].total_revenue)

		# Get input costs from Fertilizer Applications
		input_data = frappe.db.sql("""
			SELECT SUM(total_cost) as total_input_cost
			FROM `tabFertilizer Application`
			WHERE crop_cycle = %s AND docstatus = 1
		""", self.name, as_dict=True)

		if input_data and input_data[0]:
			self.input_cost = flt(input_data[0].total_input_cost)

		self.save()
		return {
			"actual_yield": self.actual_yield,
			"revenue": self.revenue,
			"input_cost": self.input_cost,
			"profit": self.profit
		}

	@frappe.whitelist()
	def mark_completed(self):
		"""Mark the crop cycle as completed."""
		self.status = "Completed"
		self.actual_end_date = frappe.utils.today()
		self.calculate_from_records()
		frappe.msgprint(_("Crop Cycle marked as completed"))

	@frappe.whitelist()
	def get_cycle_summary(self):
		"""Get comprehensive summary of the crop cycle."""
		summary = {
			"status": self.status,
			"growth_stage": getattr(self, 'growth_stage', None),
			"start_date": self.start_date,
			"days_elapsed": frappe.utils.date_diff(frappe.utils.today(), self.start_date),
			"planted_area": getattr(self, 'planted_area', 0),
			"expected_yield": getattr(self, 'expected_yield', 0),
			"actual_yield": getattr(self, 'actual_yield', 0),
			"yield_percentage": getattr(self, 'yield_percentage', 0),
			"total_cost": getattr(self, 'total_cost', 0),
			"revenue": getattr(self, 'revenue', 0),
			"profit": getattr(self, 'profit', 0),
			"disease_count": len(self.detected_disease) if self.detected_disease else 0,
			"harvest_count": frappe.db.count("Harvest Record", {"crop_cycle": self.name, "docstatus": 1}),
			"application_count": frappe.db.count("Fertilizer Application", {"crop_cycle": self.name, "docstatus": 1})
		}
		return summary

	def set_missing_values(self):
		crop = frappe.get_doc('Crop', self.crop)

		if not self.crop_spacing_uom:
			self.crop_spacing_uom = crop.crop_spacing_uom

		if not self.row_spacing_uom:
			self.row_spacing_uom = crop.row_spacing_uom

	def create_crop_cycle_project(self):
		crop = frappe.get_doc('Crop', self.crop)

		self.project = self.create_project(crop.period, crop.agriculture_task)
		self.create_task(crop.agriculture_task, self.project, self.start_date)

	def create_tasks_for_diseases(self):
		for disease in self.detected_disease:
			if not disease.tasks_created:
				self.import_disease_tasks(disease.disease, disease.start_date)
				disease.tasks_created = True

				frappe.msgprint(_("Tasks have been created for managing the {0} disease (on row {1})").format(disease.disease, disease.idx))

	def import_disease_tasks(self, disease, start_date):
		disease_doc = frappe.get_doc('Disease', disease)
		self.create_task(disease_doc.treatment_task, self.project, start_date)

	def create_project(self, period, crop_tasks):
		project = frappe.get_doc({
			"doctype": "Project",
			"project_name": self.title,
			"expected_start_date": self.start_date,
			"expected_end_date": add_days(self.start_date, period - 1)
		}).insert()

		return project.name

	def create_task(self, crop_tasks, project_name, start_date):
		for crop_task in crop_tasks:
			frappe.get_doc({
				"doctype": "Task",
				"subject": crop_task.get("task_name"),
				"priority": crop_task.get("priority"),
				"project": project_name,
				"exp_start_date": add_days(start_date, crop_task.get("start_day") - 1),
				"exp_end_date": add_days(start_date, crop_task.get("end_day") - 1)
			}).insert()

	@frappe.whitelist()
	def reload_linked_analysis(self):
		linked_doctypes = ['Soil Texture', 'Soil Analysis', 'Plant Analysis']
		required_fields = ['location', 'name', 'collection_datetime']
		output = {}

		for doctype in linked_doctypes:
			output[doctype] = frappe.get_all(doctype, fields=required_fields)

		output['Location'] = []

		for location in self.linked_location:
			output['Location'].append(frappe.get_doc('Location', location.location))

		frappe.publish_realtime("List of Linked Docs",
								output, user=frappe.session.user)

	@frappe.whitelist()
	def append_to_child(self, obj_to_append):
		for doctype in obj_to_append:
			for doc_name in set(obj_to_append[doctype]):
				self.append(doctype, {doctype: doc_name})

		self.save()


def get_coordinates(doc):
	return ast.literal_eval(doc.location).get('features')[0].get('geometry').get('coordinates')


def get_geometry_type(doc):
	return ast.literal_eval(doc.location).get('features')[0].get('geometry').get('type')


def is_in_location(point, vs):
	x, y = point
	inside = False

	j = len(vs) - 1
	i = 0

	while i < len(vs):
		xi, yi = vs[i]
		xj, yj = vs[j]

		intersect = ((yi > y) != (yj > y)) and (
			x < (xj - xi) * (y - yi) / (yj - yi) + xi)

		if intersect:
			inside = not inside

		i = j
		j += 1

	return inside
