// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Harvest Record', {
	refresh: function(frm) {
		// Set query filters
		frm.set_query('crop_cycle', function() {
			return {
				filters: {
					'docstatus': ['!=', 2]
				}
			};
		});

		frm.set_query('storage_warehouse', function() {
			return {
				filters: {
					'is_group': 0
				}
			};
		});

		// Add dashboard info
		if (!frm.is_new() && frm.doc.harvested_quantity) {
			let yield_info = '';
			if (frm.doc.yield_percentage) {
				let color = frm.doc.yield_percentage >= 100 ? 'green' :
				           frm.doc.yield_percentage >= 80 ? 'blue' :
				           frm.doc.yield_percentage >= 60 ? 'orange' : 'red';
				yield_info = `<span class="indicator ${color}">Yield: ${frm.doc.yield_percentage.toFixed(1)}%</span>`;
			}
			frm.dashboard.set_headline(yield_info);
		}

		// Add quick actions
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Fetch from Crop Cycle'), function() {
				if (frm.doc.crop_cycle) {
					frm.call('get_crop_cycle_details').then(r => {
						if (r.message) {
							frm.set_value('crop', r.message.crop);
							if (r.message.expected_yield) {
								frm.set_value('expected_quantity', r.message.expected_yield);
							}
							frappe.msgprint(__('Details fetched from Crop Cycle'));
						}
					});
				} else {
					frappe.msgprint(__('Please select a Crop Cycle first'));
				}
			});
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
						if (r.message.expected_yield) {
							frm.set_value('expected_quantity', r.message.expected_yield);
						}
					}
				}
			});
		}
	},

	harvested_quantity: function(frm) {
		frm.trigger('calculate_values');
	},

	expected_quantity: function(frm) {
		frm.trigger('calculate_yield');
	},

	unit_price: function(frm) {
		frm.trigger('calculate_values');
	},

	quality_rejected: function(frm) {
		frm.trigger('calculate_values');
	},

	cost_of_harvest: function(frm) {
		frm.trigger('calculate_net_value');
	},

	labor_cost: function(frm) {
		frm.trigger('calculate_net_value');
	},

	calculate_yield: function(frm) {
		if (frm.doc.expected_quantity && frm.doc.expected_quantity > 0) {
			let yield_pct = (frm.doc.harvested_quantity / frm.doc.expected_quantity) * 100;
			frm.set_value('yield_percentage', yield_pct);
		}
	},

	calculate_values: function(frm) {
		frm.trigger('calculate_yield');

		if (frm.doc.unit_price && frm.doc.harvested_quantity) {
			let saleable_qty = frm.doc.harvested_quantity - (frm.doc.quality_rejected || 0);
			let total = frm.doc.unit_price * saleable_qty;
			frm.set_value('total_value', total);
			frm.set_value('estimated_value', total);
			frm.trigger('calculate_net_value');
		}
	},

	calculate_net_value: function(frm) {
		if (frm.doc.total_value) {
			let total_costs = (frm.doc.cost_of_harvest || 0) + (frm.doc.labor_cost || 0);
			frm.set_value('net_value', frm.doc.total_value - total_costs);
		}
	},

	quality_grade: function(frm) {
		// Show warning for rejected grade
		if (frm.doc.quality_grade === 'Rejected') {
			frappe.msgprint({
				title: __('Quality Rejected'),
				message: __('This harvest has been marked as rejected. Please specify the rejection reason.'),
				indicator: 'orange'
			});
			frm.set_value('quality_rejected', frm.doc.harvested_quantity);
		}
	}
});
