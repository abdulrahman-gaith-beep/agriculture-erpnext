# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)

	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"fieldname": "crop_cycle",
			"label": _("Crop Cycle"),
			"fieldtype": "Link",
			"options": "Crop Cycle",
			"width": 180
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
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "start_date",
			"label": _("Start Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "end_date",
			"label": _("End Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "planted_area",
			"label": _("Planted Area"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "expected_yield",
			"label": _("Expected Yield"),
			"fieldtype": "Float",
			"width": 110
		},
		{
			"fieldname": "actual_yield",
			"label": _("Actual Yield"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "yield_percentage",
			"label": _("Yield %"),
			"fieldtype": "Percent",
			"width": 80
		},
		{
			"fieldname": "total_cost",
			"label": _("Total Cost"),
			"fieldtype": "Currency",
			"width": 110
		},
		{
			"fieldname": "revenue",
			"label": _("Revenue"),
			"fieldtype": "Currency",
			"width": 110
		},
		{
			"fieldname": "profit",
			"label": _("Profit"),
			"fieldtype": "Currency",
			"width": 110
		},
		{
			"fieldname": "roi",
			"label": _("ROI %"),
			"fieldtype": "Percent",
			"width": 80
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)

	crop_cycles = frappe.db.sql("""
		SELECT
			name as crop_cycle,
			crop,
			farm,
			status,
			start_date,
			end_date,
			planted_area,
			expected_yield,
			actual_yield,
			yield_percentage,
			total_cost,
			revenue,
			profit
		FROM `tabCrop Cycle`
		WHERE docstatus < 2
		{conditions}
		ORDER BY start_date DESC
	""".format(conditions=conditions), filters, as_dict=1)

	for row in crop_cycles:
		# Calculate ROI
		if row.total_cost and row.total_cost > 0:
			row["roi"] = (flt(row.profit) / flt(row.total_cost)) * 100
		else:
			row["roi"] = 0

	return crop_cycles


def get_conditions(filters):
	conditions = []

	if filters.get("farm"):
		conditions.append("farm = %(farm)s")

	if filters.get("crop"):
		conditions.append("crop = %(crop)s")

	if filters.get("status"):
		conditions.append("status = %(status)s")

	if filters.get("from_date"):
		conditions.append("start_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("start_date <= %(to_date)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart(data):
	if not data:
		return None

	labels = []
	yield_data = []
	profit_data = []

	for row in data[:10]:  # Top 10 for chart
		labels.append(row.get("crop_cycle", "")[:20])
		yield_data.append(flt(row.get("yield_percentage", 0)))
		profit_data.append(flt(row.get("profit", 0)))

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Yield %"),
					"values": yield_data,
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

	total_cycles = len(data)
	total_area = sum(flt(d.get("planted_area", 0)) for d in data)
	total_yield = sum(flt(d.get("actual_yield", 0)) for d in data)
	total_cost = sum(flt(d.get("total_cost", 0)) for d in data)
	total_revenue = sum(flt(d.get("revenue", 0)) for d in data)
	total_profit = sum(flt(d.get("profit", 0)) for d in data)

	avg_yield_pct = sum(flt(d.get("yield_percentage", 0)) for d in data) / total_cycles if total_cycles else 0

	return [
		{
			"value": total_cycles,
			"indicator": "Blue",
			"label": _("Total Cycles"),
			"datatype": "Int"
		},
		{
			"value": total_area,
			"indicator": "Green",
			"label": _("Total Area"),
			"datatype": "Float"
		},
		{
			"value": total_yield,
			"indicator": "Green",
			"label": _("Total Yield"),
			"datatype": "Float"
		},
		{
			"value": avg_yield_pct,
			"indicator": "Blue",
			"label": _("Avg Yield %"),
			"datatype": "Percent"
		},
		{
			"value": total_cost,
			"indicator": "Orange",
			"label": _("Total Cost"),
			"datatype": "Currency"
		},
		{
			"value": total_revenue,
			"indicator": "Green",
			"label": _("Total Revenue"),
			"datatype": "Currency"
		},
		{
			"value": total_profit,
			"indicator": "Green" if total_profit >= 0 else "Red",
			"label": _("Total Profit"),
			"datatype": "Currency"
		}
	]
