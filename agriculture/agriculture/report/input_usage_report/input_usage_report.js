// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Input Usage Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
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
			fieldname: "input_type",
			label: __("Input Type"),
			fieldtype: "Select",
			options: "\nFertilizer\nPesticide\nAll",
			default: "All"
		},
		{
			fieldname: "farm",
			label: __("Farm"),
			fieldtype: "Link",
			options: "Farm"
		},
		{
			fieldname: "crop",
			label: __("Crop"),
			fieldtype: "Link",
			options: "Crop"
		},
		{
			fieldname: "crop_cycle",
			label: __("Crop Cycle"),
			fieldtype: "Link",
			options: "Crop Cycle",
			get_query: function() {
				let farm = frappe.query_report.get_filter_value("farm");
				let crop = frappe.query_report.get_filter_value("crop");
				let filters = {};
				if (farm) filters.farm = farm;
				if (crop) filters.crop = crop;
				return { filters: filters };
			}
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "None\nFarm\nCrop\nInput\nMonth",
			default: "None"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "total_cost" && data && data.total_cost > 1000) {
			value = "<span style='color:orange;font-weight:bold'>" + value + "</span>";
		}

		if (column.fieldname === "input_type") {
			if (data && data.input_type === "Fertilizer") {
				value = "<span style='color:green'>" + value + "</span>";
			} else if (data && data.input_type === "Pesticide") {
				value = "<span style='color:red'>" + value + "</span>";
			}
		}

		return value;
	}
};
