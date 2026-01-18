// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fertilizer Application', {
	refresh: function(frm) {
		// Set query filters
		frm.set_query('crop_cycle', function() {
			return {
				filters: {
					'docstatus': ['!=', 2]
				}
			};
		});

		frm.set_query('item', function() {
			return {
				filters: {
					'item_group': ['in', ['Fertilizer', 'Pesticide', 'Seeds', 'Agricultural Inputs']]
				}
			};
		});

		// Show withholding period warning
		if (frm.doc.safe_harvest_date && frm.doc.docstatus === 1) {
			let safe_date = frappe.datetime.str_to_obj(frm.doc.safe_harvest_date);
			let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
			let days_remaining = frappe.datetime.get_diff(safe_date, today);

			if (days_remaining > 0) {
				frm.dashboard.set_headline(
					__('Safe harvest date: {0} ({1} days remaining)', [frm.doc.safe_harvest_date, days_remaining]),
					'orange'
				);
			} else {
				frm.dashboard.set_headline(
					__('Safe for harvest since {0}', [frm.doc.safe_harvest_date]),
					'green'
				);
			}
		}

		// Add quick actions
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Fetch Fertilizer Details'), function() {
				if (frm.doc.fertilizer) {
					frm.call('get_fertilizer_details').then(r => {
						if (r.message) {
							if (r.message.item) {
								frm.set_value('item', r.message.item);
							}
							frappe.msgprint(__('Fertilizer details fetched'));
						}
					});
				} else {
					frappe.msgprint(__('Please select a Fertilizer first'));
				}
			});
		}

		// Mark organic-certified applications
		if (frm.doc.is_organic_approved) {
			frm.dashboard.add_indicator(__('Organic Approved'), 'green');
		}
	},

	crop_cycle: function(frm) {
		if (frm.doc.crop_cycle) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Crop Cycle',
					name: frm.doc.crop_cycle
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('crop', r.message.crop);
						if (r.message.farm) {
							frm.set_value('farm', r.message.farm);
						}
					}
				}
			});
		}
	},

	fertilizer: function(frm) {
		if (frm.doc.fertilizer) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Fertilizer',
					name: frm.doc.fertilizer
				},
				callback: function(r) {
					if (r.message) {
						if (r.message.item) {
							frm.set_value('item', r.message.item);
						}
					}
				}
			});
		}
	},

	quantity_applied: function(frm) {
		frm.trigger('calculate_rate');
		frm.trigger('calculate_total_cost');
	},

	coverage_area: function(frm) {
		frm.trigger('calculate_rate');
	},

	unit_cost: function(frm) {
		frm.trigger('calculate_total_cost');
	},

	application_date: function(frm) {
		frm.trigger('calculate_safe_harvest_date');
	},

	withholding_period_days: function(frm) {
		frm.trigger('calculate_safe_harvest_date');
	},

	calculate_rate: function(frm) {
		if (frm.doc.quantity_applied && frm.doc.coverage_area && frm.doc.coverage_area > 0) {
			let rate = (frm.doc.quantity_applied / frm.doc.coverage_area).toFixed(3);
			frm.set_value('application_rate', `${rate} ${frm.doc.quantity_uom || ''} per ${frm.doc.area_uom || 'unit'}`);
		}
	},

	calculate_total_cost: function(frm) {
		if (frm.doc.unit_cost && frm.doc.quantity_applied) {
			frm.set_value('total_cost', frm.doc.unit_cost * frm.doc.quantity_applied);
		}
	},

	calculate_safe_harvest_date: function(frm) {
		if (frm.doc.withholding_period_days && frm.doc.application_date) {
			let safe_date = frappe.datetime.add_days(frm.doc.application_date, frm.doc.withholding_period_days);
			frm.set_value('safe_harvest_date', safe_date);
		}
	},

	application_type: function(frm) {
		// Set is_organic_approved default based on type
		if (['Organic Amendment', 'Bio-stimulant'].includes(frm.doc.application_type)) {
			frm.set_value('is_organic_approved', 1);
		}
	}
});
