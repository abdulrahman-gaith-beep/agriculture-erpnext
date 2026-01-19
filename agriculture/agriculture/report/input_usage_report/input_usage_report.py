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
	columns = [
		{
			"fieldname": "application_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "input_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "input_name",
			"label": _("Input Name"),
			"fieldtype": "Data",
			"width": 150
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
			"fieldname": "crop",
			"label": _("Crop"),
			"fieldtype": "Link",
			"options": "Crop",
			"width": 100
		},
		{
			"fieldname": "quantity",
			"label": _("Quantity"),
			"fieldtype": "Float",
			"width": 90
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Data",
			"width": 70
		},
		{
			"fieldname": "area_covered",
			"label": _("Area"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "application_method",
			"label": _("Method"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "total_cost",
			"label": _("Cost"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "applied_by",
			"label": _("Applied By"),
			"fieldtype": "Data",
			"width": 120
		}
	]

	return columns


def get_data(filters):
	data = []

	input_type = filters.get("input_type", "All")

	# Get fertilizer applications
	if input_type in ("All", "Fertilizer"):
		fertilizer_data = get_fertilizer_applications(filters)
		data.extend(fertilizer_data)

	# Get pesticide applications
	if input_type in ("All", "Pesticide"):
		pesticide_data = get_pesticide_applications(filters)
		data.extend(pesticide_data)

	# Sort by date
	data.sort(key=lambda x: x.get("application_date") or "", reverse=True)

	# Group if required
	group_by = filters.get("group_by")
	if group_by and group_by != "None":
		data = group_data(data, group_by)

	return data


def get_fertilizer_applications(filters):
	conditions = get_conditions(filters, "fertilizer")

	applications = frappe.db.sql("""
		SELECT
			fa.name as reference,
			fa.application_date,
			'Fertilizer' as input_type,
			fa.fertilizer as input_name,
			fa.farm,
			fa.crop_cycle,
			cc.crop,
			fa.quantity,
			fa.quantity_uom as uom,
			fa.area_covered,
			fa.application_method,
			fa.total_cost,
			fa.applied_by
		FROM `tabFertilizer Application` fa
		LEFT JOIN `tabCrop Cycle` cc ON fa.crop_cycle = cc.name
		WHERE fa.docstatus < 2
		{conditions}
		ORDER BY fa.application_date DESC
	""".format(conditions=conditions), filters, as_dict=1)

	return applications


def get_pesticide_applications(filters):
	conditions = get_conditions(filters, "pesticide")

	applications = frappe.db.sql("""
		SELECT
			pa.name as reference,
			pa.application_date,
			'Pesticide' as input_type,
			pa.pesticide_name as input_name,
			pa.farm,
			pa.crop_cycle,
			cc.crop,
			pa.quantity,
			pa.quantity_uom as uom,
			pa.area_covered,
			pa.application_method,
			pa.total_cost,
			pa.applied_by
		FROM `tabPesticide Application` pa
		LEFT JOIN `tabCrop Cycle` cc ON pa.crop_cycle = cc.name
		WHERE pa.docstatus < 2
		{conditions}
		ORDER BY pa.application_date DESC
	""".format(conditions=conditions), filters, as_dict=1)

	return applications


def get_conditions(filters, app_type):
	conditions = []
	prefix = "fa" if app_type == "fertilizer" else "pa"

	if filters.get("from_date"):
		conditions.append(f"{prefix}.application_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append(f"{prefix}.application_date <= %(to_date)s")

	if filters.get("farm"):
		conditions.append(f"{prefix}.farm = %(farm)s")

	if filters.get("crop_cycle"):
		conditions.append(f"{prefix}.crop_cycle = %(crop_cycle)s")

	if filters.get("crop"):
		conditions.append("cc.crop = %(crop)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


def group_data(data, group_by):
	"""Group data by specified field"""
	grouped = {}

	for row in data:
		if group_by == "Farm":
			key = row.get("farm") or "Unknown"
		elif group_by == "Crop":
			key = row.get("crop") or "Unknown"
		elif group_by == "Input":
			key = row.get("input_name") or "Unknown"
		elif group_by == "Month":
			date = row.get("application_date")
			if date:
				key = getdate(date).strftime("%Y-%m")
			else:
				key = "Unknown"
		else:
			key = "All"

		if key not in grouped:
			grouped[key] = {
				"group_key": key,
				"input_type": "Mixed",
				"input_name": key,
				"quantity": 0,
				"area_covered": 0,
				"total_cost": 0,
				"count": 0
			}

		grouped[key]["quantity"] += flt(row.get("quantity", 0))
		grouped[key]["area_covered"] += flt(row.get("area_covered", 0))
		grouped[key]["total_cost"] += flt(row.get("total_cost", 0))
		grouped[key]["count"] += 1

	# Convert to list and add group labels
	result = []
	for key, value in sorted(grouped.items()):
		value["application_date"] = None
		value["farm"] = key if group_by == "Farm" else None
		value["crop"] = key if group_by == "Crop" else None
		result.append(value)

	return result


def get_chart(data, filters):
	if not data:
		return None

	group_by = filters.get("group_by", "None")

	if group_by != "None":
		# Chart for grouped data
		labels = [d.get("group_key", "Unknown")[:15] for d in data[:10]]
		costs = [flt(d.get("total_cost", 0)) for d in data[:10]]

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

	# Chart by input type for ungrouped data
	fertilizer_cost = sum(flt(d.get("total_cost", 0)) for d in data if d.get("input_type") == "Fertilizer")
	pesticide_cost = sum(flt(d.get("total_cost", 0)) for d in data if d.get("input_type") == "Pesticide")

	return {
		"data": {
			"labels": [_("Fertilizer"), _("Pesticide")],
			"datasets": [
				{
					"name": _("Cost"),
					"values": [fertilizer_cost, pesticide_cost]
				}
			]
		},
		"type": "pie",
		"height": 300
	}


def get_summary(data):
	if not data:
		return []

	total_applications = len(data)
	fertilizer_count = sum(1 for d in data if d.get("input_type") == "Fertilizer")
	pesticide_count = sum(1 for d in data if d.get("input_type") == "Pesticide")
	total_quantity = sum(flt(d.get("quantity", 0)) for d in data)
	total_area = sum(flt(d.get("area_covered", 0)) for d in data)
	total_cost = sum(flt(d.get("total_cost", 0)) for d in data)

	fertilizer_cost = sum(flt(d.get("total_cost", 0)) for d in data if d.get("input_type") == "Fertilizer")
	pesticide_cost = sum(flt(d.get("total_cost", 0)) for d in data if d.get("input_type") == "Pesticide")

	return [
		{
			"value": total_applications,
			"indicator": "Blue",
			"label": _("Total Applications"),
			"datatype": "Int"
		},
		{
			"value": fertilizer_count,
			"indicator": "Green",
			"label": _("Fertilizer Applications"),
			"datatype": "Int"
		},
		{
			"value": pesticide_count,
			"indicator": "Orange",
			"label": _("Pesticide Applications"),
			"datatype": "Int"
		},
		{
			"value": total_area,
			"indicator": "Blue",
			"label": _("Total Area Covered"),
			"datatype": "Float"
		},
		{
			"value": fertilizer_cost,
			"indicator": "Green",
			"label": _("Fertilizer Cost"),
			"datatype": "Currency"
		},
		{
			"value": pesticide_cost,
			"indicator": "Orange",
			"label": _("Pesticide Cost"),
			"datatype": "Currency"
		},
		{
			"value": total_cost,
			"indicator": "Red",
			"label": _("Total Input Cost"),
			"datatype": "Currency"
		}
	]
