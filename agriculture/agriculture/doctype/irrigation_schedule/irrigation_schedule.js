// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Irrigation Schedule', {
	refresh: function(frm) {
		// Show next irrigation info
		if (frm.doc.next_irrigation_date && frm.doc.status === 'Active') {
			let next_date = frappe.datetime.str_to_obj(frm.doc.next_irrigation_date);
			let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
			let days_until = frappe.datetime.get_diff(next_date, today);

			if (days_until === 0) {
				frm.dashboard.set_headline(__('Irrigation scheduled for today at {0}', [frm.doc.preferred_time || 'any time']), 'blue');
			} else if (days_until === 1) {
				frm.dashboard.set_headline(__('Next irrigation tomorrow'), 'green');
			} else if (days_until > 1) {
				frm.dashboard.set_headline(__('Next irrigation in {0} days', [days_until]), 'green');
			}
		}

		// Add action buttons
		if (!frm.is_new() && frm.doc.status === 'Active') {
			frm.add_custom_button(__('Log Irrigation'), function() {
				frappe.prompt([
					{
						fieldname: 'actual_volume',
						label: __('Actual Volume'),
						fieldtype: 'Float',
						default: frm.doc.water_volume_per_event
					},
					{
						fieldname: 'duration',
						label: __('Duration (minutes)'),
						fieldtype: 'Int',
						default: frm.doc.duration_minutes
					},
					{
						fieldname: 'notes',
						label: __('Notes'),
						fieldtype: 'Small Text'
					}
				], function(values) {
					frm.call('log_irrigation_event', {
						actual_volume: values.actual_volume,
						duration: values.duration,
						notes: values.notes,
						skipped: false
					}).then(r => {
						frappe.msgprint(__('Irrigation event logged'));
						frm.reload_doc();
					});
				}, __('Log Irrigation Event'), __('Log'));
			}, __('Actions'));

			frm.add_custom_button(__('Skip Irrigation'), function() {
				frappe.prompt([
					{
						fieldname: 'reason',
						label: __('Reason for Skipping'),
						fieldtype: 'Small Text',
						reqd: 1
					}
				], function(values) {
					frm.call('log_irrigation_event', {
						skipped: true,
						notes: values.reason
					}).then(r => {
						frappe.msgprint(__('Irrigation skipped'));
						frm.reload_doc();
					});
				}, __('Skip Irrigation'), __('Skip'));
			}, __('Actions'));

			frm.add_custom_button(__('Check Weather & Irrigate'), function() {
				frm.call('check_weather_and_irrigate').then(r => {
					if (r.message) {
						frappe.msgprint(__('Weather check completed'));
						frm.reload_doc();
					}
				});
			}, __('Actions'));

			frm.add_custom_button(__('Water Usage Summary'), function() {
				frm.call('get_water_usage_summary').then(r => {
					if (r.message) {
						let summary = r.message;
						let msg = `
							<table class="table table-bordered">
								<tr><td><strong>Total Water Used</strong></td><td>${summary.total_water_used} ${frm.doc.volume_uom || 'L'}</td></tr>
								<tr><td><strong>Events Completed</strong></td><td>${summary.events_completed}</td></tr>
								<tr><td><strong>Events Skipped</strong></td><td>${summary.events_skipped}</td></tr>
								<tr><td><strong>Average per Event</strong></td><td>${summary.average_per_event} ${frm.doc.volume_uom || 'L'}</td></tr>
								<tr><td><strong>Total Cost</strong></td><td>${format_currency(summary.total_cost)}</td></tr>
								<tr><td><strong>Next Irrigation</strong></td><td>${summary.next_irrigation || 'Not scheduled'}</td></tr>
							</table>
						`;
						frappe.msgprint({
							title: __('Water Usage Summary'),
							message: msg,
							indicator: 'blue'
						});
					}
				});
			});
		}

		// Show water savings indicator
		if (frm.doc.events_skipped > 0) {
			let savings = frm.doc.events_skipped * (frm.doc.water_volume_per_event || 0);
			if (savings > 0) {
				frm.dashboard.add_indicator(__('Water Saved: {0} {1}', [savings, frm.doc.volume_uom || 'L']), 'green');
			}
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
					}
				}
			});
		}
	},

	frequency: function(frm) {
		// Auto-set title based on frequency
		if (!frm.doc.title && frm.doc.frequency) {
			let location = frm.doc.field_name || frm.doc.farm || 'Field';
			frm.set_value('title', `Irrigation - ${location} - ${frm.doc.frequency}`);
		}
	},

	water_volume_per_event: function(frm) {
		frm.trigger('calculate_flow_rate');
	},

	duration_minutes: function(frm) {
		frm.trigger('calculate_flow_rate');
	},

	calculate_flow_rate: function(frm) {
		if (frm.doc.water_volume_per_event && frm.doc.duration_minutes) {
			let flow_rate = frm.doc.water_volume_per_event / frm.doc.duration_minutes;
			frm.set_value('flow_rate', flow_rate.toFixed(2));
		}
	}
});
