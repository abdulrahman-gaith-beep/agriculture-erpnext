// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crop Inspection', {
	refresh: function(frm) {
		// Show status indicator
		if (frm.doc.status === 'Action Required') {
			frm.dashboard.set_headline(__('Immediate attention required'), 'red');
		} else if (frm.doc.immediate_action_required) {
			frm.dashboard.set_headline(__('Immediate action flagged'), 'orange');
		}

		// Add action buttons
		if (!frm.is_new()) {
			frm.add_custom_button(__('Create Follow-up Inspection'), function() {
				frm.call('create_follow_up_inspection').then(r => {
					if (r.message) {
						frappe.set_route('Form', 'Crop Inspection', r.message);
					}
				});
			}, __('Actions'));

			frm.add_custom_button(__('View History'), function() {
				frm.call('get_historical_data').then(r => {
					if (r.message && r.message.length > 0) {
						show_historical_data(r.message);
					} else {
						frappe.msgprint(__('No historical inspection data found'));
					}
				});
			}, __('Actions'));

			// Quick links to related documents
			if (frm.doc.crop_cycle) {
				frm.add_custom_button(__('View Crop Cycle'), function() {
					frappe.set_route('Form', 'Crop Cycle', frm.doc.crop_cycle);
				}, __('Links'));
			}

			if (frm.doc.farm) {
				frm.add_custom_button(__('View Farm'), function() {
					frappe.set_route('Form', 'Farm', frm.doc.farm);
				}, __('Links'));
			}
		}

		// Show health indicators
		if (frm.doc.overall_health_rating) {
			let rating = frm.doc.overall_health_rating;
			let color = rating >= 4 ? 'green' : (rating >= 2.5 ? 'orange' : 'red');
			frm.dashboard.add_indicator(__('Health: {0}/5', [rating]), color);
		}

		if (frm.doc.pest_severity && frm.doc.pest_severity !== 'None') {
			let color = ['High', 'Severe'].includes(frm.doc.pest_severity) ? 'red' : 'orange';
			frm.dashboard.add_indicator(__('Pest: {0}', [frm.doc.pest_severity]), color);
		}

		if (frm.doc.disease_severity && frm.doc.disease_severity !== 'None') {
			let color = ['High', 'Severe'].includes(frm.doc.disease_severity) ? 'red' : 'orange';
			frm.dashboard.add_indicator(__('Disease: {0}', [frm.doc.disease_severity]), color);
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
						frm.set_value('farm', r.message.farm);
						if (r.message.growth_stage) {
							frm.set_value('growth_stage', r.message.growth_stage);
						}
					}
				}
			});
		}
	},

	inspection_type: function(frm) {
		// Set default inspection date
		if (!frm.doc.inspection_date) {
			frm.set_value('inspection_date', frappe.datetime.get_today());
		}

		// Set inspected by to current user
		if (!frm.doc.inspected_by) {
			frm.set_value('inspected_by', frappe.session.user);
		}
	},

	immediate_action_required: function(frm) {
		if (frm.doc.immediate_action_required) {
			frm.set_value('status', 'Action Required');
			frappe.show_alert({
				message: __('Status set to Action Required'),
				indicator: 'orange'
			});
		}
	},

	pest_severity: function(frm) {
		check_severity_status(frm);
	},

	disease_severity: function(frm) {
		check_severity_status(frm);
	},

	vigor_rating: function(frm) {
		if (['Poor', 'Critical'].includes(frm.doc.vigor_rating) && frm.doc.status !== 'Action Required') {
			frm.set_value('status', 'Action Required');
			frappe.show_alert({
				message: __('Status set to Action Required due to poor crop vigor'),
				indicator: 'orange'
			});
		}
	},

	follow_up_required: function(frm) {
		if (frm.doc.follow_up_required && !frm.doc.follow_up_date) {
			// Set default follow-up date to 7 days from inspection
			let follow_up = frappe.datetime.add_days(frm.doc.inspection_date || frappe.datetime.get_today(), 7);
			frm.set_value('follow_up_date', follow_up);
		}
	}
});

function check_severity_status(frm) {
	let high_severity = ['High', 'Severe'];
	if (high_severity.includes(frm.doc.pest_severity) || high_severity.includes(frm.doc.disease_severity)) {
		if (frm.doc.status !== 'Action Required') {
			frm.set_value('status', 'Action Required');
			frappe.show_alert({
				message: __('Status set to Action Required due to high severity issues'),
				indicator: 'orange'
			});
		}
	}
}

function show_historical_data(data) {
	let html = '<table class="table table-bordered">';
	html += '<thead><tr>';
	html += '<th>Date</th><th>Type</th><th>Status</th><th>Health</th><th>Pest</th><th>Disease</th>';
	html += '</tr></thead><tbody>';

	data.forEach(function(row) {
		html += '<tr>';
		html += `<td><a href="/app/crop-inspection/${row.name}">${row.inspection_date}</a></td>`;
		html += `<td>${row.inspection_type || '-'}</td>`;
		html += `<td>${row.status || '-'}</td>`;
		html += `<td>${row.overall_health_rating || '-'}</td>`;
		html += `<td>${row.pest_severity || 'None'}</td>`;
		html += `<td>${row.disease_severity || 'None'}</td>`;
		html += '</tr>';
	});

	html += '</tbody></table>';

	frappe.msgprint({
		title: __('Inspection History'),
		message: html,
		indicator: 'blue'
	});
}
