# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart(data, filters)
	summary = get_summary(data)

	return columns, data, None, chart, summary


def get_columns(filters):
	group_by = filters.get("group_by", "None")

	columns = [
		{
			"fieldname": "activity_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "labor_activity",
			"label": _("Activity"),
			"fieldtype": "Link",
			"options": "Labor Activity",
			"width": 150
		},
		{
			"fieldname": "activity_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "farm",
			"label": _("Farm"),
			"fieldtype": "Link",
			"options": "Farm",
			"width": 120
		},
		{
			"fieldname": "crop_cycle",
			"label": _("Crop Cycle"),
			"fieldtype": "Link",
			"options": "Crop Cycle",
			"width": 150
		},
		{
			"fieldname": "worker_count",
			"label": _("Workers"),
			"fieldtype": "Int",
			"width": 70
		},
		{
			"fieldname": "regular_hours",
			"label": _("Regular Hrs"),
			"fieldtype": "Float",
			"width": 90
		},
		{
			"fieldname": "overtime_hours",
			"label": _("OT Hrs"),
			"fieldtype": "Float",
			"width": 70
		},
		{
			"fieldname": "total_hours",
			"label": _("Total Hrs"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "regular_cost",
			"label": _("Regular Cost"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "overtime_cost",
			"label": _("OT Cost"),
			"fieldtype": "Currency",
			"width": 90
		},
		{
			"fieldname": "total_cost",
			"label": _("Total Cost"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "cost_per_hour",
			"label": _("Cost/Hr"),
			"fieldtype": "Currency",
			"width": 80
		}
	]

	return columns


def get_data(filters):
	conditions = get_conditions(filters)

	activities = frappe.db.sql("""
		SELECT
			la.name as labor_activity,
			la.activity_date,
			la.activity_type,
			la.farm,
			la.crop_cycle,
			la.number_of_workers as worker_count,
			la.regular_hours,
			la.overtime_hours,
			la.total_hours,
			la.regular_cost,
			la.overtime_cost,
			la.total_cost,
			la.supervisor
		FROM `tabLabor Activity` la
		WHERE la.docstatus < 2
		{conditions}
		ORDER BY la.activity_date DESC
	""".format(conditions=conditions), filters, as_dict=1)

	# Calculate cost per hour
	for row in activities:
		if flt(row.total_hours) > 0:
			row["cost_per_hour"] = flt(row.total_cost) / flt(row.total_hours)
		else:
			row["cost_per_hour"] = 0

	# Group if required
	group_by = filters.get("group_by")
	if group_by and group_by != "None":
		activities = group_data(activities, group_by)

	return activities


def get_conditions(filters):
	conditions = []

	if filters.get("from_date"):
		conditions.append("la.activity_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("la.activity_date <= %(to_date)s")

	if filters.get("farm"):
		conditions.append("la.farm = %(farm)s")

	if filters.get("crop_cycle"):
		conditions.append("la.crop_cycle = %(crop_cycle)s")

	if filters.get("activity_type"):
		conditions.append("la.activity_type = %(activity_type)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


def group_data(data, group_by):
	"""Group data by specified field"""
	grouped = {}

	for row in data:
		if group_by == "Farm":
			key = row.get("farm") or "Unknown"
		elif group_by == "Activity Type":
			key = row.get("activity_type") or "Unknown"
		elif group_by == "Crop Cycle":
			key = row.get("crop_cycle") or "Unknown"
		elif group_by == "Worker":
			key = row.get("supervisor") or "Unknown"
		elif group_by == "Week":
			date = row.get("activity_date")
			if date:
				# Get week start date
				d = getdate(date)
				week_start = d - frappe.utils.datetime.timedelta(days=d.weekday())
				key = week_start.strftime("%Y-W%W")
			else:
				key = "Unknown"
		else:
			key = "All"

		if key not in grouped:
			grouped[key] = {
				"group_key": key,
				"labor_activity": f"{len(grouped) + 1} activities",
				"activity_type": key if group_by == "Activity Type" else "Mixed",
				"worker_count": 0,
				"regular_hours": 0,
				"overtime_hours": 0,
				"total_hours": 0,
				"regular_cost": 0,
				"overtime_cost": 0,
				"total_cost": 0,
				"count": 0
			}

		grouped[key]["worker_count"] += flt(row.get("worker_count", 0))
		grouped[key]["regular_hours"] += flt(row.get("regular_hours", 0))
		grouped[key]["overtime_hours"] += flt(row.get("overtime_hours", 0))
		grouped[key]["total_hours"] += flt(row.get("total_hours", 0))
		grouped[key]["regular_cost"] += flt(row.get("regular_cost", 0))
		grouped[key]["overtime_cost"] += flt(row.get("overtime_cost", 0))
		grouped[key]["total_cost"] += flt(row.get("total_cost", 0))
		grouped[key]["count"] += 1

	# Convert to list and calculate averages
	result = []
	for key, value in sorted(grouped.items()):
		value["activity_date"] = None
		value["farm"] = key if group_by == "Farm" else None
		value["crop_cycle"] = key if group_by == "Crop Cycle" else None
		value["labor_activity"] = f"{value['count']} activities"

		if flt(value["total_hours"]) > 0:
			value["cost_per_hour"] = flt(value["total_cost"]) / flt(value["total_hours"])
		else:
			value["cost_per_hour"] = 0

		result.append(value)

	return result


def get_chart(data, filters):
	if not data:
		return None

	group_by = filters.get("group_by", "None")

	if group_by != "None":
		labels = [str(d.get("group_key", "Unknown"))[:15] for d in data[:10]]
		costs = [flt(d.get("total_cost", 0)) for d in data[:10]]
		hours = [flt(d.get("total_hours", 0)) for d in data[:10]]

		return {
			"data": {
				"labels": labels,
				"datasets": [
					{
						"name": _("Total Cost"),
						"values": costs,
						"chartType": "bar"
					}
				]
			},
			"type": "bar",
			"height": 300
		}

	# Chart by activity type for ungrouped data
	activity_costs = {}
	for row in data:
		activity_type = row.get("activity_type") or "Other"
		if activity_type not in activity_costs:
			activity_costs[activity_type] = 0
		activity_costs[activity_type] += flt(row.get("total_cost", 0))

	sorted_activities = sorted(activity_costs.items(), key=lambda x: x[1], reverse=True)[:8]
	labels = [a[0] for a in sorted_activities]
	values = [a[1] for a in sorted_activities]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Cost by Activity"),
					"values": values
				}
			]
		},
		"type": "bar",
		"height": 300
	}


def get_summary(data):
	if not data:
		return []

	total_activities = len(data)
	total_workers = sum(flt(d.get("worker_count", 0)) for d in data)
	total_regular_hours = sum(flt(d.get("regular_hours", 0)) for d in data)
	total_overtime_hours = sum(flt(d.get("overtime_hours", 0)) for d in data)
	total_hours = sum(flt(d.get("total_hours", 0)) for d in data)
	total_regular_cost = sum(flt(d.get("regular_cost", 0)) for d in data)
	total_overtime_cost = sum(flt(d.get("overtime_cost", 0)) for d in data)
	total_cost = sum(flt(d.get("total_cost", 0)) for d in data)

	avg_cost_per_hour = total_cost / total_hours if total_hours > 0 else 0
	overtime_percentage = (total_overtime_hours / total_hours * 100) if total_hours > 0 else 0

	return [
		{
			"value": total_activities,
			"indicator": "Blue",
			"label": _("Total Activities"),
			"datatype": "Int"
		},
		{
			"value": total_workers,
			"indicator": "Blue",
			"label": _("Total Worker-Days"),
			"datatype": "Int"
		},
		{
			"value": total_regular_hours,
			"indicator": "Green",
			"label": _("Regular Hours"),
			"datatype": "Float"
		},
		{
			"value": total_overtime_hours,
			"indicator": "Orange",
			"label": _("Overtime Hours"),
			"datatype": "Float"
		},
		{
			"value": overtime_percentage,
			"indicator": "Orange" if overtime_percentage > 20 else "Green",
			"label": _("Overtime %"),
			"datatype": "Percent"
		},
		{
			"value": total_regular_cost,
			"indicator": "Green",
			"label": _("Regular Cost"),
			"datatype": "Currency"
		},
		{
			"value": total_overtime_cost,
			"indicator": "Orange",
			"label": _("Overtime Cost"),
			"datatype": "Currency"
		},
		{
			"value": total_cost,
			"indicator": "Red",
			"label": _("Total Labor Cost"),
			"datatype": "Currency"
		},
		{
			"value": avg_cost_per_hour,
			"indicator": "Blue",
			"label": _("Avg Cost/Hour"),
			"datatype": "Currency"
		}
	]
