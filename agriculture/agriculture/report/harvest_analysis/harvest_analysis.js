// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Harvest Analysis"] = {
	"filters": [
		{
			"fieldname": "farm",
			"label": __("Farm"),
			"fieldtype": "Link",
			"options": "Farm"
		},
		{
			"fieldname": "crop",
			"label": __("Crop"),
			"fieldtype": "Link",
			"options": "Crop"
		},
		{
			"fieldname": "crop_cycle",
			"label": __("Crop Cycle"),
			"fieldtype": "Link",
			"options": "Crop Cycle"
		},
		{
			"fieldname": "quality_grade",
			"label": __("Quality Grade"),
			"fieldtype": "Select",
			"options": "\nPremium\nGrade A\nGrade B\nGrade C\nReject"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date"
		}
	]
};
