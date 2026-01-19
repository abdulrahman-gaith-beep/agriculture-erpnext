# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class CropCalendarItem(Document):
	def validate(self):
		self.calculate_expected_revenue()

	def calculate_expected_revenue(self):
		"""Calculate expected revenue from yield and price."""
		if self.expected_yield and self.expected_price_per_unit:
			self.expected_revenue = flt(self.expected_yield) * flt(self.expected_price_per_unit)
