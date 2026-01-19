# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data, filters)
	summary = get_summary(data)

	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"fieldname": "harvest_record",
			"label": _("Harvest Record"),
			"fieldtype": "Link",
			"options": "Harvest Record",
			"width": 150
		},
		{
			"fieldname": "crop_cycle",
			"label": _("Crop Cycle"),
			"fieldtype": "Link",
			"options": "Crop Cycle",
			"width": 150
		},
		{
			"fieldname": "crop",
			"label": _("Crop"),
			"fieldtype": "Link",
			"options": "Crop",
			"width": 120
		},
		{
			"fieldname": "farm",
			"label": _("Farm"),
			"fieldtype": "Link",
			"options": "Farm",
			"width": 120
		},
		{
			"fieldname": "harvest_date",
			"label": _("Harvest Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "harvest_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "gross_quantity",
			"label": _("Gross Qty"),
			"fieldtype": "Float",
			"width": 90
		},
		{
			"fieldname": "net_quantity",
			"label": _("Net Qty"),
			"fieldtype": "Float",
			"width": 90
		},
		{
			"fieldname": "quality_grade",
			"label": _("Quality"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "yield_percentage",
			"label": _("Yield %"),
			"fieldtype": "Percent",
			"width": 80
		},
		{
			"fieldname": "unit_price",
			"label": _("Unit Price"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "total_value",
			"label": _("Total Value"),
			"fieldtype": "Currency",
			"width": 110
		},
		{
			"fieldname": "labor_cost",
			"label": _("Labor Cost"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "net_revenue",
			"label": _("Net Revenue"),
			"fieldtype": "Currency",
			"width": 110
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)

	harvests = frappe.db.sql("""
		SELECT
			name as harvest_record,
			crop_cycle,
			crop,
			farm,
			harvest_date,
			harvest_type,
			gross_quantity,
			net_quantity,
			quality_grade,
			yield_percentage,
			unit_price,
			total_value,
			labor_cost,
			net_revenue
		FROM `tabHarvest Record`
		WHERE docstatus < 2
		{conditions}
		ORDER BY harvest_date DESC
	""".format(conditions=conditions), filters, as_dict=1)

	return harvests


def get_conditions(filters):
	conditions = []

	if filters.get("farm"):
		conditions.append("farm = %(farm)s")

	if filters.get("crop"):
		conditions.append("crop = %(crop)s")

	if filters.get("crop_cycle"):
		conditions.append("crop_cycle = %(crop_cycle)s")

	if filters.get("quality_grade"):
		conditions.append("quality_grade = %(quality_grade)s")

	if filters.get("from_date"):
		conditions.append("harvest_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("harvest_date <= %(to_date)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart(data, filters):
	if not data:
		return None

	# Group by crop for chart
	crop_totals = {}
	for row in data:
		crop = row.get("crop") or "Unknown"
		if crop not in crop_totals:
			crop_totals[crop] = {"quantity": 0, "value": 0}
		crop_totals[crop]["quantity"] += flt(row.get("net_quantity", 0))
		crop_totals[crop]["value"] += flt(row.get("total_value", 0))

	labels = list(crop_totals.keys())[:10]
	quantity_data = [crop_totals[crop]["quantity"] for crop in labels]
	value_data = [crop_totals[crop]["value"] for crop in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Quantity"),
					"values": quantity_data,
					"chartType": "bar"
				}
			]
		},
		"type": "bar",
		"height": 300
	}


def get_summary(data):
	if not data:
		return []

	total_harvests = len(data)
	total_gross = sum(flt(d.get("gross_quantity", 0)) for d in data)
	total_net = sum(flt(d.get("net_quantity", 0)) for d in data)
	total_value = sum(flt(d.get("total_value", 0)) for d in data)
	total_labor = sum(flt(d.get("labor_cost", 0)) for d in data)
	total_net_revenue = sum(flt(d.get("net_revenue", 0)) for d in data)

	# Calculate average quality (only where yield_percentage exists)
	yields = [flt(d.get("yield_percentage", 0)) for d in data if d.get("yield_percentage")]
	avg_yield = sum(yields) / len(yields) if yields else 0

	# Count by quality grade
	grade_counts = {}
	for row in data:
		grade = row.get("quality_grade") or "Ungraded"
		grade_counts[grade] = grade_counts.get(grade, 0) + 1

	return [
		{
			"value": total_harvests,
			"indicator": "Blue",
			"label": _("Total Harvests"),
			"datatype": "Int"
		},
		{
			"value": total_gross,
			"indicator": "Green",
			"label": _("Gross Quantity"),
			"datatype": "Float"
		},
		{
			"value": total_net,
			"indicator": "Green",
			"label": _("Net Quantity"),
			"datatype": "Float"
		},
		{
			"value": avg_yield,
			"indicator": "Blue",
			"label": _("Avg Yield %"),
			"datatype": "Percent"
		},
		{
			"value": total_value,
			"indicator": "Green",
			"label": _("Total Value"),
			"datatype": "Currency"
		},
		{
			"value": total_labor,
			"indicator": "Orange",
			"label": _("Total Labor Cost"),
			"datatype": "Currency"
		},
		{
			"value": total_net_revenue,
			"indicator": "Green" if total_net_revenue >= 0 else "Red",
			"label": _("Net Revenue"),
			"datatype": "Currency"
		}
	]
