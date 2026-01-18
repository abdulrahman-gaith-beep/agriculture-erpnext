# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Scheduled tasks for the Agriculture module.

These tasks run automatically based on the scheduler configuration in hooks.py:
- Daily: check_crop_cycle_status, check_analysis_reminders
- Weekly: calculate_crop_cycle_financials
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today


def check_crop_cycle_status():
	"""
	Check and update crop cycle statuses.

	- Mark cycles as 'Active' if they've started
	- Mark cycles as 'Harvesting' if past expected harvest date
	- Send notifications for upcoming harvest dates
	"""
	today_date = getdate(today())

	# Update Planning -> Active for started cycles
	cycles_to_activate = frappe.get_all(
		"Crop Cycle",
		filters={
			"status": "Planning",
			"start_date": ["<=", today_date]
		},
		pluck="name"
	)

	for cycle_name in cycles_to_activate:
		frappe.db.set_value("Crop Cycle", cycle_name, "status", "Active")

	# Check for cycles approaching harvest (project end date)
	cycles_near_harvest = frappe.db.sql("""
		SELECT cc.name, cc.title, cc.crop, p.expected_end_date
		FROM `tabCrop Cycle` cc
		JOIN `tabProject` p ON cc.project = p.name
		WHERE cc.status = 'Active'
		AND p.expected_end_date BETWEEN %s AND %s
	""", (today_date, add_days(today_date, 7)), as_dict=True)

	for cycle in cycles_near_harvest:
		days_remaining = (getdate(cycle.expected_end_date) - today_date).days
		if days_remaining <= 7:
			# Send notification
			send_harvest_reminder(cycle, days_remaining)

	frappe.db.commit()


def send_harvest_reminder(cycle, days_remaining):
	"""Send harvest reminder notification."""
	try:
		# Get Agriculture Manager users
		users = frappe.get_all(
			"Has Role",
			filters={"role": "Agriculture Manager", "parenttype": "User"},
			pluck="parent"
		)

		for user in users:
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Crop Cycle",
				"document_name": cycle.name,
				"subject": _("Harvest Reminder: {0}").format(cycle.title),
				"email_content": _(
					"Crop cycle '{0}' ({1}) is expected to be ready for harvest in {2} days."
				).format(cycle.title, cycle.crop, days_remaining)
			}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error("Failed to send harvest reminder")


def check_analysis_reminders():
	"""
	Check for overdue soil and water analysis and send reminders.

	Based on the reminder days configured in Agriculture Settings.
	"""
	try:
		settings = frappe.get_single("Agriculture Settings")
		soil_reminder_days = settings.soil_testing_reminder_days or 180
		water_reminder_days = settings.water_testing_reminder_days or 90
	except Exception:
		# Settings may not exist
		soil_reminder_days = 180
		water_reminder_days = 90

	today_date = getdate(today())
	soil_threshold = add_days(today_date, -soil_reminder_days)
	water_threshold = add_days(today_date, -water_reminder_days)

	# Check farms that need soil analysis
	farms_need_soil = frappe.db.sql("""
		SELECT f.name, f.farm_name,
		       MAX(sa.collection_datetime) as last_analysis
		FROM `tabFarm` f
		LEFT JOIN `tabSoil Analysis` sa ON sa.location = f.location
		WHERE f.status = 'Active'
		GROUP BY f.name
		HAVING last_analysis IS NULL OR last_analysis < %s
	""", soil_threshold, as_dict=True)

	for farm in farms_need_soil:
		create_analysis_reminder("Soil", farm)

	# Check farms that need water analysis
	farms_need_water = frappe.db.sql("""
		SELECT f.name, f.farm_name,
		       MAX(wa.collection_datetime) as last_analysis
		FROM `tabFarm` f
		LEFT JOIN `tabWater Analysis` wa ON wa.location = f.location
		WHERE f.status = 'Active'
		GROUP BY f.name
		HAVING last_analysis IS NULL OR last_analysis < %s
	""", water_threshold, as_dict=True)

	for farm in farms_need_water:
		create_analysis_reminder("Water", farm)


def create_analysis_reminder(analysis_type, farm):
	"""Create a ToDo reminder for analysis."""
	try:
		# Check if reminder already exists
		existing = frappe.db.exists("ToDo", {
			"reference_type": "Farm",
			"reference_name": farm.name,
			"description": ["like", f"%{analysis_type} Analysis%"],
			"status": "Open"
		})

		if not existing:
			frappe.get_doc({
				"doctype": "ToDo",
				"owner": frappe.session.user,
				"reference_type": "Farm",
				"reference_name": farm.name,
				"description": _(
					"{0} Analysis due for farm '{1}'. Please schedule a {0} test."
				).format(analysis_type, farm.farm_name),
				"priority": "Medium",
				"date": today()
			}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(f"Failed to create {analysis_type} analysis reminder")


def calculate_crop_cycle_financials():
	"""
	Weekly task to recalculate financials for active crop cycles.

	Updates:
	- Input costs from Fertilizer Applications
	- Revenue and yield from Harvest Records
	- Profit calculations
	"""
	active_cycles = frappe.get_all(
		"Crop Cycle",
		filters={"status": ["in", ["Active", "Harvesting"]]},
		pluck="name"
	)

	for cycle_name in active_cycles:
		try:
			cycle = frappe.get_doc("Crop Cycle", cycle_name)

			# Get input costs from Fertilizer Applications
			input_data = frappe.db.sql("""
				SELECT COALESCE(SUM(total_cost), 0) as total_input_cost
				FROM `tabFertilizer Application`
				WHERE crop_cycle = %s AND docstatus = 1
			""", cycle_name, as_dict=True)

			if input_data:
				cycle.input_cost = input_data[0].total_input_cost

			# Get harvest data
			harvest_data = frappe.db.sql("""
				SELECT
					COALESCE(SUM(harvested_quantity), 0) as total_yield,
					COALESCE(SUM(total_value), 0) as total_revenue
				FROM `tabHarvest Record`
				WHERE crop_cycle = %s AND docstatus = 1
			""", cycle_name, as_dict=True)

			if harvest_data:
				cycle.actual_yield = harvest_data[0].total_yield
				cycle.revenue = harvest_data[0].total_revenue

			cycle.save()

		except Exception:
			frappe.log_error(f"Failed to calculate financials for {cycle_name}")

	frappe.db.commit()


def sync_weather_data():
	"""
	Sync weather data from external API.

	This is a placeholder for weather API integration.
	To enable, add to scheduler_events in hooks.py.
	"""
	try:
		settings = frappe.get_single("Agriculture Settings")

		if not settings.weather_api_provider or not settings.weather_api_key:
			return

		# Get active farms with coordinates
		farms = frappe.get_all(
			"Farm",
			filters={
				"status": "Active",
				"latitude": ["is", "set"],
				"longitude": ["is", "set"]
			},
			fields=["name", "farm_name", "latitude", "longitude", "location"]
		)

		for farm in farms:
			# API call would go here
			# weather_data = fetch_weather(
			#     settings.weather_api_provider,
			#     settings.weather_api_key,
			#     farm.latitude,
			#     farm.longitude
			# )
			pass

	except Exception:
		frappe.log_error("Failed to sync weather data")
