# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class ProduceSale(Document):
	def validate(self):
		self.validate_dates()
		self.calculate_totals()
		self.calculate_payment_pending()
		self.update_payment_status()
		self.validate_items()

	def on_submit(self):
		self.update_harvest_records()
		self.create_stock_entry()

	def on_cancel(self):
		self.reverse_harvest_records()

	def validate_dates(self):
		"""Validate date fields"""
		if self.payment_date and self.sale_date:
			if getdate(self.payment_date) < getdate(self.sale_date):
				frappe.throw(_("Payment Date cannot be before Sale Date"))

		if self.delivery_date and self.sale_date:
			if getdate(self.delivery_date) < getdate(self.sale_date):
				frappe.throw(_("Delivery Date cannot be before Sale Date"))

	def validate_items(self):
		"""Validate sale items"""
		if not self.items:
			frappe.throw(_("Please add at least one item to the sale"))

		for item in self.items:
			if flt(item.quantity) <= 0:
				frappe.throw(_("Row {0}: Quantity must be greater than zero").format(item.idx))
			if flt(item.unit_price) < 0:
				frappe.throw(_("Row {0}: Unit Price cannot be negative").format(item.idx))

	def calculate_totals(self):
		"""Calculate total quantity and amounts from items"""
		self.total_quantity = 0
		self.subtotal = 0

		for item in self.items:
			item.amount = flt(item.quantity) * flt(item.unit_price)
			self.total_quantity += flt(item.quantity)
			self.subtotal += flt(item.amount)

		# Calculate discount
		if self.discount_percentage:
			self.discount_amount = flt(self.subtotal) * flt(self.discount_percentage) / 100
		else:
			self.discount_amount = flt(self.discount_amount) or 0

		# Calculate total
		self.total_amount = flt(self.subtotal) - flt(self.discount_amount)

	def calculate_payment_pending(self):
		"""Calculate pending payment amount"""
		self.amount_pending = flt(self.total_amount) - flt(self.amount_paid)

	def update_payment_status(self):
		"""Update payment status based on amounts"""
		if flt(self.amount_paid) <= 0:
			self.payment_status = "Unpaid"
		elif flt(self.amount_paid) >= flt(self.total_amount):
			self.payment_status = "Paid"
			self.amount_pending = 0
		else:
			self.payment_status = "Partially Paid"

	def update_harvest_records(self):
		"""Link sale to harvest records and update sold quantities"""
		for item in self.items:
			if item.harvest_record:
				harvest = frappe.get_doc("Harvest Record", item.harvest_record)
				sold_qty = flt(harvest.get("sold_quantity") or 0) + flt(item.quantity)
				frappe.db.set_value("Harvest Record", item.harvest_record, "sold_quantity", sold_qty)

	def reverse_harvest_records(self):
		"""Reverse harvest record updates on cancellation"""
		for item in self.items:
			if item.harvest_record:
				harvest = frappe.get_doc("Harvest Record", item.harvest_record)
				sold_qty = flt(harvest.get("sold_quantity") or 0) - flt(item.quantity)
				frappe.db.set_value("Harvest Record", item.harvest_record, "sold_quantity", max(0, sold_qty))

	def create_stock_entry(self):
		"""Create stock entry for inventory deduction if warehouse is specified"""
		# This would integrate with ERPNext Stock module if available
		pass

	@frappe.whitelist()
	def record_payment(self, amount, payment_method=None, reference=None, payment_date=None):
		"""Record a payment against this sale"""
		if flt(amount) <= 0:
			frappe.throw(_("Payment amount must be greater than zero"))

		self.amount_paid = flt(self.amount_paid) + flt(amount)
		self.payment_method = payment_method or self.payment_method
		self.payment_reference = reference or self.payment_reference
		self.payment_date = payment_date or nowdate()

		self.calculate_payment_pending()
		self.update_payment_status()
		self.save()

		frappe.msgprint(_("Payment of {0} recorded successfully").format(
			frappe.format_value(amount, {"fieldtype": "Currency"})
		))

		return self

	@frappe.whitelist()
	def mark_delivered(self, delivery_date=None, vehicle_number=None, driver_name=None):
		"""Mark the sale as delivered"""
		self.delivery_status = "Delivered"
		self.delivery_date = delivery_date or nowdate()
		if vehicle_number:
			self.vehicle_number = vehicle_number
		if driver_name:
			self.driver_name = driver_name

		# Update main status if payment is complete
		if self.payment_status == "Paid":
			self.status = "Paid"
		else:
			self.status = "Delivered"

		self.save()
		frappe.msgprint(_("Sale marked as delivered"))
		return self

	@frappe.whitelist()
	def create_invoice(self):
		"""Create a Sales Invoice linked to this produce sale"""
		# This would integrate with ERPNext Accounts if available
		frappe.msgprint(_("Invoice creation requires ERPNext Accounts module"))
		return None


@frappe.whitelist()
def get_available_harvests(crop=None, farm=None):
	"""Get harvests with available quantity for sale"""
	filters = {"docstatus": 1}
	if crop:
		filters["crop"] = crop
	if farm:
		filters["farm"] = farm

	harvests = frappe.get_all(
		"Harvest Record",
		filters=filters,
		fields=["name", "crop", "farm", "harvest_date", "net_quantity", "quality_grade", "unit_price"],
		order_by="harvest_date desc"
	)

	# Calculate available quantity
	for h in harvests:
		sold_qty = flt(frappe.db.get_value("Harvest Record", h.name, "sold_quantity") or 0)
		h["available_quantity"] = flt(h.net_quantity) - sold_qty

	# Filter out fully sold harvests
	return [h for h in harvests if h["available_quantity"] > 0]


@frappe.whitelist()
def get_customer_sales_summary(customer_name):
	"""Get sales summary for a customer"""
	sales = frappe.get_all(
		"Produce Sale",
		filters={"customer_name": customer_name, "docstatus": 1},
		fields=["name", "sale_date", "total_amount", "payment_status"]
	)

	total_sales = len(sales)
	total_value = sum(flt(s.total_amount) for s in sales)
	unpaid = sum(1 for s in sales if s.payment_status != "Paid")

	return {
		"total_sales": total_sales,
		"total_value": total_value,
		"unpaid_sales": unpaid,
		"recent_sales": sales[:5]
	}
