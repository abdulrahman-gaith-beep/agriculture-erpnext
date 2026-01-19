# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, now_datetime, today


class IrrigationSchedule(Document):
	"""
	Irrigation Schedule manages water application schedules for crops.

	Features:
	- Multiple frequency options (daily, weekly, etc.)
	- Sensor-based and weather-responsive automation
	- Water usage tracking and cost calculation
	- Integration with weather data for smart scheduling
	"""

	def validate(self):
		self.validate_dates()
		self.calculate_next_irrigation()
		self.calculate_costs()
		self.set_title()

	def set_title(self):
		"""Auto-generate title if not set."""
		if not self.title:
			location = self.field_name or self.farm or "Field"
			self.title = f"Irrigation - {location} - {self.frequency}"

	def validate_dates(self):
		"""Validate schedule dates."""
		if self.end_date and self.start_date:
			if getdate(self.end_date) < getdate(self.start_date):
				frappe.throw(_("End date cannot be before start date"))

		if self.end_date and getdate(self.end_date) < getdate(today()):
			if self.status == "Active":
				self.status = "Completed"

	def calculate_next_irrigation(self):
		"""Calculate the next irrigation date based on frequency."""
		if self.status != "Active":
			self.next_irrigation_date = None
			return

		base_date = getdate(self.last_irrigated) if self.last_irrigated else getdate(self.start_date)

		frequency_days = {
			"Daily": 1,
			"Every 2 Days": 2,
			"Every 3 Days": 3,
			"Twice Weekly": 3,
			"Weekly": 7,
			"Bi-Weekly": 14,
			"As Needed": 0
		}

		days = frequency_days.get(self.frequency, 1)
		if days > 0:
			next_date = add_days(base_date, days)
			# If next date is in the past, calculate from today
			if getdate(next_date) < getdate(today()):
				next_date = add_days(today(), 1)
			self.next_irrigation_date = next_date

	def calculate_costs(self):
		"""Calculate total irrigation cost."""
		if self.events_completed and self.events_completed > 0:
			water_cost = flt(self.water_cost_per_unit) * flt(self.water_volume_per_event) * self.events_completed
			energy_cost = flt(self.energy_cost_per_event) * self.events_completed
			self.total_cost = water_cost + energy_cost

	@frappe.whitelist()
	def log_irrigation_event(self, actual_volume=None, duration=None, notes=None, skipped=False):
		"""Log an irrigation event."""
		event = {
			"event_date": today(),
			"event_time": now_datetime().strftime("%H:%M:%S"),
			"scheduled_volume": self.water_volume_per_event,
			"actual_volume": actual_volume or self.water_volume_per_event,
			"duration_minutes": duration or self.duration_minutes,
			"was_skipped": skipped,
			"notes": notes
		}

		self.append("irrigation_events", event)

		if skipped:
			self.events_skipped = (self.events_skipped or 0) + 1
		else:
			self.events_completed = (self.events_completed or 0) + 1
			self.last_irrigated = now_datetime()
			self.total_water_used = flt(self.total_water_used) + flt(event["actual_volume"])

		self.calculate_next_irrigation()
		self.calculate_costs()
		self.save()

		return {"status": "success", "next_irrigation": self.next_irrigation_date}

	@frappe.whitelist()
	def check_weather_and_irrigate(self):
		"""Check weather conditions before irrigation."""
		should_irrigate = True
		skip_reason = None

		# Check temperature conditions
		if self.min_temperature or self.max_temperature:
			# Get current weather if available
			weather = get_latest_weather(self.location or self.farm)
			if weather:
				if self.min_temperature and weather.get("temperature") < self.min_temperature:
					should_irrigate = False
					skip_reason = f"Temperature ({weather.get('temperature')}C) below minimum ({self.min_temperature}C)"
				if self.max_temperature and weather.get("temperature") > self.max_temperature:
					should_irrigate = False
					skip_reason = f"Temperature ({weather.get('temperature')}C) above maximum ({self.max_temperature}C)"

		# Check rain forecast
		if self.skip_if_rain_forecast:
			# Placeholder for weather API integration
			rain_forecast = get_rain_forecast(self.location or self.farm)
			if rain_forecast and rain_forecast > (self.rain_threshold_mm or 5):
				should_irrigate = False
				skip_reason = f"Rain forecasted ({rain_forecast}mm exceeds threshold)"

		if should_irrigate:
			return self.log_irrigation_event()
		else:
			return self.log_irrigation_event(skipped=True, notes=skip_reason)

	@frappe.whitelist()
	def get_water_usage_summary(self):
		"""Get water usage statistics."""
		return {
			"total_water_used": self.total_water_used or 0,
			"events_completed": self.events_completed or 0,
			"events_skipped": self.events_skipped or 0,
			"average_per_event": flt(self.total_water_used / self.events_completed, 2) if self.events_completed else 0,
			"total_cost": self.total_cost or 0,
			"next_irrigation": self.next_irrigation_date
		}


def get_latest_weather(location):
	"""Get latest weather data for location."""
	if not location:
		return None

	weather = frappe.db.sql("""
		SELECT name, weather_date
		FROM `tabWeather`
		WHERE location = %s
		ORDER BY weather_date DESC
		LIMIT 1
	""", location, as_dict=True)

	if weather:
		# Return weather parameters
		params = frappe.get_all(
			"Weather Parameter",
			filters={"parent": weather[0].name},
			fields=["criteria", "value"]
		)
		return {p.criteria: p.value for p in params}

	return None


def get_rain_forecast(location):
	"""Get rain forecast - placeholder for weather API."""
	# This would integrate with a weather API
	return None


@frappe.whitelist()
def get_irrigation_due_today():
	"""Get all irrigation schedules due today."""
	return frappe.get_all(
		"Irrigation Schedule",
		filters={
			"status": "Active",
			"next_irrigation_date": today()
		},
		fields=["name", "title", "crop_cycle", "farm", "field_name", "preferred_time", "water_volume_per_event"]
	)
