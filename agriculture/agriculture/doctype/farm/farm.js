// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Farm', {
	refresh: function(frm) {
		// Add custom buttons
		if (!frm.is_new()) {
			frm.add_custom_button(__('View Crop Cycles'), function() {
				frappe.set_route('List', 'Crop Cycle', {
					farm: frm.doc.name
				});
			}, __('View'));

			frm.add_custom_button(__('New Crop Cycle'), function() {
				frappe.new_doc('Crop Cycle', {
					farm: frm.doc.name
				});
			}, __('Create'));

			frm.add_custom_button(__('New Soil Analysis'), function() {
				frappe.new_doc('Soil Analysis', {
					location: frm.doc.location
				});
			}, __('Create'));

			frm.add_custom_button(__('Farm Summary'), function() {
				frm.call('get_farm_summary').then(r => {
					if (r.message) {
						let summary = r.message;
						let msg = `
							<table class="table table-bordered">
								<tr><td><strong>Total Area</strong></td><td>${summary.total_area} ${frm.doc.area_uom}</td></tr>
								<tr><td><strong>Cultivable Area</strong></td><td>${summary.cultivable_area} ${frm.doc.area_uom}</td></tr>
								<tr><td><strong>Irrigated Area</strong></td><td>${summary.irrigated_area} ${frm.doc.area_uom}</td></tr>
								<tr><td><strong>Fields/Plots</strong></td><td>${summary.field_count}</td></tr>
								<tr><td><strong>Water Sources</strong></td><td>${summary.water_source_count}</td></tr>
								<tr><td><strong>Active Crop Cycles</strong></td><td>${summary.active_crop_cycles}</td></tr>
								<tr><td><strong>Organic Certified</strong></td><td>${summary.is_organic ? 'Yes' : 'No'}</td></tr>
							</table>
						`;
						frappe.msgprint({
							title: __('Farm Summary'),
							message: msg,
							indicator: 'blue'
						});
					}
				});
			});
		}

		// Show certification warning
		if (frm.doc.is_organic_certified && frm.doc.organic_valid_until) {
			let valid_until = frappe.datetime.str_to_obj(frm.doc.organic_valid_until);
			let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
			let days_until = frappe.datetime.get_diff(valid_until, today);

			if (days_until < 0) {
				frm.dashboard.set_headline(__('Organic certification has expired!'), 'red');
			} else if (days_until < 30) {
				frm.dashboard.set_headline(
					__('Organic certification expires in {0} days', [days_until]),
					'orange'
				);
			}
		}
	},

	total_area: function(frm) {
		frm.trigger('calculate_non_cultivable');
	},

	cultivable_area: function(frm) {
		frm.trigger('calculate_non_cultivable');
	},

	calculate_non_cultivable: function(frm) {
		if (frm.doc.total_area && frm.doc.cultivable_area) {
			let non_cultivable = frm.doc.total_area - frm.doc.cultivable_area;
			if (non_cultivable >= 0) {
				frm.set_value('non_cultivable_area', non_cultivable);
			}
		}
	},

	location: function(frm) {
		// Fetch coordinates from Location if available
		if (frm.doc.location) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Location',
					name: frm.doc.location
				},
				callback: function(r) {
					if (r.message && r.message.location) {
						// Parse GeoJSON to extract coordinates
						try {
							let geojson = JSON.parse(r.message.location);
							if (geojson.features && geojson.features[0]) {
								let coords = geojson.features[0].geometry.coordinates;
								if (coords) {
									// For point geometry
									if (typeof coords[0] === 'number') {
										frm.set_value('longitude', coords[0]);
										frm.set_value('latitude', coords[1]);
									}
								}
							}
						} catch (e) {
							console.log('Could not parse location coordinates');
						}
					}
				}
			});
		}
	}
});
