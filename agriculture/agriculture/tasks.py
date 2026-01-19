# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Scheduled tasks for the Agriculture module.

These tasks run automatically based on the scheduler configuration in hooks.py:
- Daily: check_crop_cycle_status, check_analysis_reminders, check_irrigation_schedules,
         check_equipment_maintenance, check_pesticide_safety_periods
- Weekly: calculate_crop_cycle_financials, generate_crop_health_summary
- Monthly: generate_monthly_reports
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today, nowdate, flt


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


def check_irrigation_schedules():
	"""
	Check irrigation schedules and send reminders for upcoming irrigations.
	"""
	today_date = getdate(today())

	# Find schedules due today or tomorrow
	upcoming_schedules = frappe.get_all(
		"Irrigation Schedule",
		filters={
			"status": ["in", ["Scheduled", "In Progress"]],
			"scheduled_date": ["between", [today_date, add_days(today_date, 1)]]
		},
		fields=["name", "farm", "crop_cycle", "scheduled_date", "water_source", "irrigation_method"]
	)

	for schedule in upcoming_schedules:
		try:
			# Create reminder ToDo
			existing = frappe.db.exists("ToDo", {
				"reference_type": "Irrigation Schedule",
				"reference_name": schedule.name,
				"status": "Open"
			})

			if not existing:
				frappe.get_doc({
					"doctype": "ToDo",
					"owner": frappe.session.user,
					"reference_type": "Irrigation Schedule",
					"reference_name": schedule.name,
					"description": _(
						"Irrigation scheduled for {0} using {1}. Farm: {2}"
					).format(schedule.scheduled_date, schedule.irrigation_method, schedule.farm),
					"priority": "High",
					"date": schedule.scheduled_date
				}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(f"Failed to create irrigation reminder for {schedule.name}")

	frappe.db.commit()


def check_equipment_maintenance():
	"""
	Check for equipment due for maintenance and send reminders.
	"""
	today_date = getdate(today())
	next_week = add_days(today_date, 7)

	# Find equipment due for service
	equipment_due = frappe.get_all(
		"Farm Equipment",
		filters={
			"status": ["in", ["Active", "Needs Service"]],
			"next_service_date": ["<=", next_week]
		},
		fields=["name", "equipment_name", "equipment_type", "next_service_date"]
	)

	for equipment in equipment_due:
		try:
			# Update status if past due
			if equipment.next_service_date and getdate(equipment.next_service_date) <= today_date:
				frappe.db.set_value("Farm Equipment", equipment.name, "status", "Needs Service")

			# Create reminder ToDo
			existing = frappe.db.exists("ToDo", {
				"reference_type": "Farm Equipment",
				"reference_name": equipment.name,
				"description": ["like", "%maintenance%"],
				"status": "Open"
			})

			if not existing:
				days_until = (getdate(equipment.next_service_date) - today_date).days
				if days_until < 0:
					priority = "High"
					message = _("Equipment '{0}' is overdue for maintenance by {1} days!").format(
						equipment.equipment_name, abs(days_until)
					)
				else:
					priority = "Medium"
					message = _("Equipment '{0}' is due for maintenance in {1} days.").format(
						equipment.equipment_name, days_until
					)

				frappe.get_doc({
					"doctype": "ToDo",
					"owner": frappe.session.user,
					"reference_type": "Farm Equipment",
					"reference_name": equipment.name,
					"description": message,
					"priority": priority,
					"date": equipment.next_service_date or today()
				}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(f"Failed to create equipment maintenance reminder for {equipment.name}")

	frappe.db.commit()


def check_pesticide_safety_periods():
	"""
	Check for crops approaching or past their safe harvest dates after pesticide application.
	"""
	today_date = getdate(today())

	# Find recent pesticide applications that may affect harvest
	applications = frappe.get_all(
		"Pesticide Application",
		filters={
			"docstatus": 1,
			"safe_harvest_date": [">=", add_days(today_date, -7)],
			"safe_harvest_date": ["<=", add_days(today_date, 7)]
		},
		fields=["name", "crop_cycle", "pesticide_name", "safe_harvest_date", "application_date"]
	)

	for app in applications:
		try:
			safe_date = getdate(app.safe_harvest_date)
			days_until_safe = (safe_date - today_date).days

			if days_until_safe > 0:
				# Still in safety period
				message = _(
					"Crop cycle {0} treated with {1} on {2}. Safe to harvest in {3} days ({4})."
				).format(app.crop_cycle, app.pesticide_name, app.application_date,
						days_until_safe, app.safe_harvest_date)
				priority = "High" if days_until_safe <= 3 else "Medium"
			else:
				# Past safety period - safe to harvest
				message = _(
					"Crop cycle {0} treated with {1} is now safe to harvest (PHI completed on {2})."
				).format(app.crop_cycle, app.pesticide_name, app.safe_harvest_date)
				priority = "Low"

			# Create notification
			existing = frappe.db.exists("ToDo", {
				"reference_type": "Pesticide Application",
				"reference_name": app.name,
				"status": "Open"
			})

			if not existing and days_until_safe > 0:
				frappe.get_doc({
					"doctype": "ToDo",
					"owner": frappe.session.user,
					"reference_type": "Pesticide Application",
					"reference_name": app.name,
					"description": message,
					"priority": priority,
					"date": app.safe_harvest_date
				}).insert(ignore_permissions=True)

		except Exception:
			frappe.log_error(f"Failed to check safety period for {app.name}")

	frappe.db.commit()


def calculate_crop_cycle_financials():
	"""
	Weekly task to recalculate financials for active crop cycles.

	Updates:
	- Input costs from Fertilizer and Pesticide Applications
	- Labor costs from Labor Activities
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

			# Get fertilizer costs
			fertilizer_cost = frappe.db.sql("""
				SELECT COALESCE(SUM(total_cost), 0) as cost
				FROM `tabFertilizer Application`
				WHERE crop_cycle = %s AND docstatus = 1
			""", cycle_name, as_dict=True)[0].cost

			# Get pesticide costs
			pesticide_cost = frappe.db.sql("""
				SELECT COALESCE(SUM(total_cost), 0) as cost
				FROM `tabPesticide Application`
				WHERE crop_cycle = %s AND docstatus = 1
			""", cycle_name, as_dict=True)[0].cost

			# Get labor costs
			labor_cost = frappe.db.sql("""
				SELECT COALESCE(SUM(total_cost), 0) as cost
				FROM `tabLabor Activity`
				WHERE crop_cycle = %s AND docstatus < 2
			""", cycle_name, as_dict=True)[0].cost

			# Total input cost
			cycle.input_cost = flt(fertilizer_cost) + flt(pesticide_cost)
			if hasattr(cycle, 'labor_cost'):
				cycle.labor_cost = flt(labor_cost)

			# Calculate total cost
			cycle.total_cost = flt(cycle.input_cost) + flt(labor_cost)

			# Get harvest data
			harvest_data = frappe.db.sql("""
				SELECT
					COALESCE(SUM(net_quantity), 0) as total_yield,
					COALESCE(SUM(total_value), 0) as total_revenue
				FROM `tabHarvest Record`
				WHERE crop_cycle = %s AND docstatus = 1
			""", cycle_name, as_dict=True)

			if harvest_data:
				cycle.actual_yield = harvest_data[0].total_yield
				cycle.revenue = harvest_data[0].total_revenue

			# Calculate profit
			cycle.profit = flt(cycle.revenue) - flt(cycle.total_cost)

			# Calculate yield percentage
			if cycle.expected_yield and flt(cycle.expected_yield) > 0:
				cycle.yield_percentage = (flt(cycle.actual_yield) / flt(cycle.expected_yield)) * 100

			cycle.save()

		except Exception:
			frappe.log_error(f"Failed to calculate financials for {cycle_name}")

	frappe.db.commit()


def generate_crop_health_summary():
	"""
	Weekly task to generate crop health summaries from inspection data.
	"""
	today_date = getdate(today())
	week_ago = add_days(today_date, -7)

	# Get active crop cycles
	active_cycles = frappe.get_all(
		"Crop Cycle",
		filters={"status": "Active"},
		fields=["name", "title", "crop", "farm"]
	)

	for cycle in active_cycles:
		try:
			# Get recent inspections
			inspections = frappe.get_all(
				"Crop Inspection",
				filters={
					"crop_cycle": cycle.name,
					"inspection_date": [">=", week_ago],
					"docstatus": 1
				},
				fields=["overall_health_score", "pest_severity", "disease_severity", "stress_level"]
			)

			if not inspections:
				continue

			# Calculate averages
			health_scores = [i.overall_health_score for i in inspections if i.overall_health_score]
			avg_health = sum(health_scores) / len(health_scores) if health_scores else 0

			# Count issues
			pest_issues = sum(1 for i in inspections if i.pest_severity in ["Moderate", "Severe", "Critical"])
			disease_issues = sum(1 for i in inspections if i.disease_severity in ["Moderate", "Severe", "Critical"])
			stress_issues = sum(1 for i in inspections if i.stress_level in ["Moderate", "High", "Severe"])

			# Create health summary notification if issues found
			if pest_issues > 0 or disease_issues > 0 or avg_health < 60:
				message = _(
					"Weekly Health Summary for {0}:\n"
					"- Average Health Score: {1}%\n"
					"- Pest Issues: {2}\n"
					"- Disease Issues: {3}\n"
					"- Stress Issues: {4}"
				).format(cycle.title, round(avg_health, 1), pest_issues, disease_issues, stress_issues)

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
						"subject": _("Weekly Crop Health Summary: {0}").format(cycle.title),
						"email_content": message
					}).insert(ignore_permissions=True)

		except Exception:
			frappe.log_error(f"Failed to generate health summary for {cycle.name}")

	frappe.db.commit()


def generate_monthly_reports():
	"""
	Monthly task to generate summary reports for management.
	"""
	today_date = getdate(today())
	month_ago = add_days(today_date, -30)

	try:
		# Gather monthly statistics
		stats = {}

		# Harvest statistics
		harvest_stats = frappe.db.sql("""
			SELECT
				COUNT(*) as harvest_count,
				COALESCE(SUM(net_quantity), 0) as total_quantity,
				COALESCE(SUM(total_value), 0) as total_value
			FROM `tabHarvest Record`
			WHERE harvest_date >= %s AND docstatus = 1
		""", month_ago, as_dict=True)[0]
		stats["harvests"] = harvest_stats

		# Labor statistics
		labor_stats = frappe.db.sql("""
			SELECT
				COUNT(*) as activity_count,
				COALESCE(SUM(total_hours), 0) as total_hours,
				COALESCE(SUM(total_cost), 0) as total_cost
			FROM `tabLabor Activity`
			WHERE activity_date >= %s AND docstatus < 2
		""", month_ago, as_dict=True)[0]
		stats["labor"] = labor_stats

		# Input usage statistics
		fertilizer_stats = frappe.db.sql("""
			SELECT
				COUNT(*) as application_count,
				COALESCE(SUM(total_cost), 0) as total_cost
			FROM `tabFertilizer Application`
			WHERE application_date >= %s AND docstatus = 1
		""", month_ago, as_dict=True)[0]

		pesticide_stats = frappe.db.sql("""
			SELECT
				COUNT(*) as application_count,
				COALESCE(SUM(total_cost), 0) as total_cost
			FROM `tabPesticide Application`
			WHERE application_date >= %s AND docstatus = 1
		""", month_ago, as_dict=True)[0]

		stats["inputs"] = {
			"fertilizer_applications": fertilizer_stats.application_count,
			"fertilizer_cost": fertilizer_stats.total_cost,
			"pesticide_applications": pesticide_stats.application_count,
			"pesticide_cost": pesticide_stats.total_cost
		}

		# Sales statistics
		sales_stats = frappe.db.sql("""
			SELECT
				COUNT(*) as sale_count,
				COALESCE(SUM(total_amount), 0) as total_revenue,
				COALESCE(SUM(amount_pending), 0) as pending_amount
			FROM `tabProduce Sale`
			WHERE sale_date >= %s AND docstatus = 1
		""", month_ago, as_dict=True)[0]
		stats["sales"] = sales_stats

		# Create summary message
		message = _("""
Monthly Agriculture Report ({0} to {1})

HARVESTS:
- Total Harvests: {2}
- Total Quantity: {3}
- Total Value: {4}

LABOR:
- Activities: {5}
- Total Hours: {6}
- Total Cost: {7}

INPUTS:
- Fertilizer Applications: {8} (Cost: {9})
- Pesticide Applications: {10} (Cost: {11})

SALES:
- Total Sales: {12}
- Total Revenue: {13}
- Pending Payments: {14}
		""").format(
			month_ago, today_date,
			stats["harvests"]["harvest_count"],
			stats["harvests"]["total_quantity"],
			frappe.format_value(stats["harvests"]["total_value"], {"fieldtype": "Currency"}),
			stats["labor"]["activity_count"],
			stats["labor"]["total_hours"],
			frappe.format_value(stats["labor"]["total_cost"], {"fieldtype": "Currency"}),
			stats["inputs"]["fertilizer_applications"],
			frappe.format_value(stats["inputs"]["fertilizer_cost"], {"fieldtype": "Currency"}),
			stats["inputs"]["pesticide_applications"],
			frappe.format_value(stats["inputs"]["pesticide_cost"], {"fieldtype": "Currency"}),
			stats["sales"]["sale_count"],
			frappe.format_value(stats["sales"]["total_revenue"], {"fieldtype": "Currency"}),
			frappe.format_value(stats["sales"]["pending_amount"], {"fieldtype": "Currency"})
		)

		# Send to Agriculture Managers
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
				"document_type": "Agriculture Settings",
				"document_name": "Agriculture Settings",
				"subject": _("Monthly Agriculture Report - {0}").format(today_date.strftime("%B %Y")),
				"email_content": message
			}).insert(ignore_permissions=True)

	except Exception:
		frappe.log_error("Failed to generate monthly agriculture report")

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
