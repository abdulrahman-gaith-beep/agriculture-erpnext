# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class Weather(Document):
	def validate(self):
		self.validate_temperatures()
		self.calculate_agricultural_indices()
		self.determine_spray_conditions()
		self.determine_irrigation_recommendation()
		self.check_weather_alerts()

	def validate_temperatures(self):
		"""Validate temperature values"""
		if self.temperature_min and self.temperature_max:
			if flt(self.temperature_min) > flt(self.temperature_max):
				frappe.throw(_("Minimum temperature cannot be greater than maximum temperature"))

		if self.temperature:
			if self.temperature_min and flt(self.temperature) < flt(self.temperature_min):
				frappe.msgprint(_("Current temperature is below minimum recorded temperature"))
			if self.temperature_max and flt(self.temperature) > flt(self.temperature_max):
				frappe.msgprint(_("Current temperature is above maximum recorded temperature"))

	def calculate_agricultural_indices(self):
		"""Calculate agricultural indices based on weather data"""
		# Calculate Growing Degree Days (GDD)
		if self.temperature_min is not None and self.temperature_max is not None:
			base_temp = 10  # Base temperature for most crops
			avg_temp = (flt(self.temperature_min) + flt(self.temperature_max)) / 2
			self.growing_degree_days = max(0, avg_temp - base_temp)

		# Determine frost risk
		if self.temperature_min is not None:
			min_temp = flt(self.temperature_min)
			if min_temp <= 0:
				self.frost_risk = "Severe"
			elif min_temp <= 2:
				self.frost_risk = "High"
			elif min_temp <= 4:
				self.frost_risk = "Moderate"
			elif min_temp <= 6:
				self.frost_risk = "Low"
			else:
				self.frost_risk = "None"

		# Determine heat stress index
		if self.temperature_max is not None:
			max_temp = flt(self.temperature_max)
			humidity = flt(self.humidity) if self.humidity else 50

			# Simple heat index calculation
			if max_temp >= 40 or (max_temp >= 35 and humidity >= 60):
				self.heat_stress_index = "Severe"
			elif max_temp >= 35 or (max_temp >= 32 and humidity >= 70):
				self.heat_stress_index = "High"
			elif max_temp >= 32 or (max_temp >= 28 and humidity >= 80):
				self.heat_stress_index = "Moderate"
			elif max_temp >= 28:
				self.heat_stress_index = "Low"
			else:
				self.heat_stress_index = "None"

		# Calculate chilling hours (for fruit crops)
		if self.temperature is not None:
			temp = flt(self.temperature)
			if temp <= 7 and temp >= 0:
				# Assuming this is hourly data, otherwise it's a daily estimate
				self.chilling_hours = 1
			else:
				self.chilling_hours = 0

	def determine_spray_conditions(self):
		"""Determine if conditions are suitable for spraying pesticides/fertilizers"""
		wind_speed = flt(self.wind_speed) if self.wind_speed else 0
		humidity = flt(self.humidity) if self.humidity else 50
		temp = flt(self.temperature) if self.temperature else 25
		rainfall = flt(self.rainfall) if self.rainfall else 0
		rain_prob = flt(self.rainfall_probability) if self.rainfall_probability else 0

		# Spray not recommended conditions
		if (rainfall > 0 or rain_prob > 70 or wind_speed > 15 or
			temp > 35 or temp < 5 or humidity < 20):
			self.spray_conditions = "Not Recommended"
		elif (rain_prob > 50 or wind_speed > 12 or temp > 32 or
			  temp < 10 or humidity < 30 or humidity > 90):
			self.spray_conditions = "Poor"
		elif (rain_prob > 30 or wind_speed > 8 or temp > 30 or
			  humidity < 40 or humidity > 85):
			self.spray_conditions = "Marginal"
		elif (wind_speed > 5 or humidity < 50 or humidity > 80):
			self.spray_conditions = "Good"
		else:
			self.spray_conditions = "Excellent"

	def determine_irrigation_recommendation(self):
		"""Determine irrigation recommendation based on weather"""
		rainfall = flt(self.rainfall) if self.rainfall else 0
		rain_prob = flt(self.rainfall_probability) if self.rainfall_probability else 0
		temp = flt(self.temperature_max) if self.temperature_max else 25
		humidity = flt(self.humidity) if self.humidity else 50
		soil_moisture = flt(self.soil_moisture) if self.soil_moisture else None
		evapotranspiration = flt(self.evapotranspiration) if self.evapotranspiration else 0

		# If rain expected
		if rain_prob > 70 or rainfall > 10:
			self.irrigation_recommendation = "Delay - Rain Expected"
			return

		# If soil moisture is available, use it
		if soil_moisture is not None:
			if soil_moisture > 70:
				self.irrigation_recommendation = "Not Needed"
			elif soil_moisture > 50:
				self.irrigation_recommendation = "Light Irrigation"
			elif soil_moisture > 30:
				self.irrigation_recommendation = "Normal Irrigation"
			else:
				self.irrigation_recommendation = "Heavy Irrigation"
			return

		# Based on temperature and humidity
		if temp > 35 or (temp > 30 and humidity < 40):
			self.irrigation_recommendation = "Heavy Irrigation"
		elif temp > 28 or humidity < 50:
			self.irrigation_recommendation = "Normal Irrigation"
		elif rainfall > 5 or humidity > 80:
			self.irrigation_recommendation = "Not Needed"
		else:
			self.irrigation_recommendation = "Light Irrigation"

	def check_weather_alerts(self):
		"""Check for weather alert conditions"""
		if not self.weather_alerts or self.weather_alerts == "None":
			# Auto-detect alerts based on conditions
			temp_min = flt(self.temperature_min) if self.temperature_min else None
			temp_max = flt(self.temperature_max) if self.temperature_max else None
			rainfall = flt(self.rainfall) if self.rainfall else 0
			wind_speed = flt(self.wind_speed) if self.wind_speed else 0
			wind_gust = flt(self.wind_gust) if self.wind_gust else 0

			if temp_min is not None and temp_min <= 0:
				self.weather_alerts = "Frost Warning"
				self.alert_severity = "Warning"
			elif temp_max is not None and temp_max >= 40:
				self.weather_alerts = "Heat Wave"
				self.alert_severity = "Warning"
			elif rainfall >= 50:
				self.weather_alerts = "Heavy Rain"
				self.alert_severity = "Warning"
			elif wind_gust >= 60 or wind_speed >= 40:
				self.weather_alerts = "High Wind"
				self.alert_severity = "Warning"
			else:
				self.weather_alerts = "None"
				self.alert_severity = None

	@frappe.whitelist()
	def load_contents(self):
		"""Load weather parameters from analysis criteria"""
		docs = frappe.get_all(
			"Agriculture Analysis Criteria",
			filters={"linked_doctype": "Weather"}
		)
		for doc in docs:
			self.append("weather_parameter", {"title": str(doc.name)})

	@frappe.whitelist()
	def get_suitability_for_operation(self, operation_type):
		"""Check if weather is suitable for a specific farm operation"""
		result = {"suitable": True, "reasons": [], "recommendation": ""}

		wind_speed = flt(self.wind_speed) if self.wind_speed else 0
		temp = flt(self.temperature) if self.temperature else 25
		humidity = flt(self.humidity) if self.humidity else 50
		rainfall = flt(self.rainfall) if self.rainfall else 0
		rain_prob = flt(self.rainfall_probability) if self.rainfall_probability else 0

		if operation_type == "Spraying":
			if wind_speed > 15:
				result["suitable"] = False
				result["reasons"].append(_("Wind speed too high for spraying"))
			if rainfall > 0 or rain_prob > 50:
				result["suitable"] = False
				result["reasons"].append(_("Rain expected - spray will be washed off"))
			if temp > 35:
				result["suitable"] = False
				result["reasons"].append(_("Temperature too high - spray will evaporate"))

		elif operation_type == "Harvesting":
			if rainfall > 0 or humidity > 85:
				result["suitable"] = False
				result["reasons"].append(_("Wet conditions - produce quality may be affected"))
			if wind_speed > 40:
				result["suitable"] = False
				result["reasons"].append(_("Wind too strong for safe harvesting"))

		elif operation_type == "Planting":
			if rainfall > 20:
				result["suitable"] = False
				result["reasons"].append(_("Soil too wet for planting"))
			if temp < 5:
				result["suitable"] = False
				result["reasons"].append(_("Temperature too low for germination"))
			if temp > 40:
				result["suitable"] = False
				result["reasons"].append(_("Temperature too high - seedlings may wilt"))

		elif operation_type == "Irrigation":
			if rainfall > 10 or rain_prob > 70:
				result["suitable"] = False
				result["reasons"].append(_("Sufficient rain expected"))
				result["recommendation"] = _("Delay irrigation - rain expected")

		if result["suitable"]:
			result["recommendation"] = _("Weather conditions are suitable for {0}").format(operation_type)
		else:
			result["recommendation"] = _("Consider postponing {0}").format(operation_type)

		return result


@frappe.whitelist()
def get_weather_summary(farm=None, from_date=None, to_date=None):
	"""Get weather summary for a farm and date range"""
	filters = {}
	if farm:
		filters["farm"] = farm
	if from_date:
		filters["date"] = [">=", from_date]
	if to_date:
		if "date" in filters:
			filters["date"] = ["between", [from_date, to_date]]
		else:
			filters["date"] = ["<=", to_date]

	weather_records = frappe.get_all(
		"Weather",
		filters=filters,
		fields=[
			"date", "temperature", "temperature_min", "temperature_max",
			"humidity", "rainfall", "wind_speed"
		],
		order_by="date desc",
		limit=30
	)

	if not weather_records:
		return {"message": _("No weather data available")}

	# Calculate averages
	temps = [flt(w.temperature) for w in weather_records if w.temperature]
	humidities = [flt(w.humidity) for w in weather_records if w.humidity]
	rainfalls = [flt(w.rainfall) for w in weather_records if w.rainfall]

	return {
		"record_count": len(weather_records),
		"avg_temperature": sum(temps) / len(temps) if temps else 0,
		"max_temperature": max([flt(w.temperature_max) for w in weather_records if w.temperature_max] or [0]),
		"min_temperature": min([flt(w.temperature_min) for w in weather_records if w.temperature_min] or [0]),
		"avg_humidity": sum(humidities) / len(humidities) if humidities else 0,
		"total_rainfall": sum(rainfalls),
		"rainy_days": sum(1 for w in weather_records if flt(w.rainfall) > 0)
	}
