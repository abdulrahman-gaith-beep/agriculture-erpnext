// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Labor Cost Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "farm",
			label: __("Farm"),
			fieldtype: "Link",
			options: "Farm"
		},
		{
			fieldname: "crop_cycle",
			label: __("Crop Cycle"),
			fieldtype: "Link",
			options: "Crop Cycle",
			get_query: function() {
				let farm = frappe.query_report.get_filter_value("farm");
				if (farm) {
					return { filters: { farm: farm } };
				}
				return {};
			}
		},
		{
			fieldname: "activity_type",
			label: __("Activity Type"),
			fieldtype: "Select",
			options: "\nPlanting\nWeeding\nHarvesting\nIrrigation\nFertilizing\nSpraying\nPruning\nSoil Preparation\nTransporting\nPacking\nMaintenance\nOther"
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "None\nFarm\nActivity Type\nCrop Cycle\nWorker\nWeek",
			default: "None"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "total_cost" && data && data.total_cost > 5000) {
			value = "<span style='color:orange;font-weight:bold'>" + value + "</span>";
		}

		if (column.fieldname === "overtime_hours" && data && data.overtime_hours > 0) {
			value = "<span style='color:red'>" + value + "</span>";
		}

		return value;
	}
};
