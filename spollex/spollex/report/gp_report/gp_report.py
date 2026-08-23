# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _, qb, scrub
from frappe.query_builder import Order
from frappe.utils import cint, flt
from erpnext.controllers.queries import get_match_cond
from erpnext.stock.utils import get_incoming_rate


def execute(filters=None):
	if not filters:
		filters = frappe._dict()
	filters.currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	gross_profit_data = GrossProfitGenerator(filters)

	data = []

	group_wise_columns = frappe._dict(
		{
			"default": [
				"invoice_or_item",
				"customer",
#				"customer_group",
				"posting_date",
				"item_code",
				"item_name",
				"item_group",
#				"sales_partner_name",
#				"brand",
#				"description",
#				"warehouse",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"credit_note_total",
				"selling_total",
				"buying_amount",
				"commission_amount",
#				"incentive_amount",
				"gross_profit",
				"gross_profit_percent",
				"gross_profit_percent_on_cost",
#				"project",
				"stock_creation_documents"
			],
			"invoice": [
				"invoice_or_item",
				"customer",
				"customer_group",
				"posting_date",
				"item_code",
				"item_name",
				"item_group",
				"sales_partner_name",
#				"brand",
				"description",
				"warehouse",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"credit_note_total",
				"selling_total",
				"buying_amount",
				"commission_amount",
#				"incentive_amount",
				"gross_profit",
				"gross_profit_percent",
				"gross_profit_percent_on_cost",
#				"project",
				"stock_creation_documents"
			],
			"item_code": [
				"item_code",
				"item_name",
#				"brand",
				"description",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"credit_note_total",
				"selling_total",
				"buying_amount",
				"commission_amount",
#				"incentive_amount",
				"gross_profit",
				"gross_profit_percent",
				"gross_profit_percent_on_cost",
			],
		}
	)

	columns = get_columns(group_wise_columns, filters)

	if filters.group_by in ["Invoice", "Default"]:
		get_data_when_grouped_by_invoice(columns, gross_profit_data, filters, group_wise_columns, data)
	else:
		get_data_when_not_grouped_by_invoice(gross_profit_data, filters, group_wise_columns, data)

	return columns, data

def get_data_when_grouped_by_invoice(columns, gross_profit_data, filters, group_wise_columns, data):
	column_names = get_column_names()

	# removing Item Code and Item Name columns
	if filters.group_by == "Invoice":
		columns[0] = "Sales Invoice:Link/Item:300"
		del columns[4:6]
	else:
		# to have Sales Invoice as link field in the first column
		columns[0] = "Sales Invoice:Link/Sales Invoice:300"

	totals = init_totals()

	for src in gross_profit_data.si_list:
		row = frappe._dict()
		row.indent = src.indent
		row.parent_invoice = src.parent_invoice
		row.currency = filters.currency

		for col in group_wise_columns.get(scrub(filters.group_by)):
			row[column_names[col]] = src.get(col)

		if src.indent == 1:
			update_totals(totals, src)

		if filters.group_by == "Invoice" or (filters.group_by == "Default" and src.indent == 1):
			data.append(row)
	calculate_gross_profit_percentages(totals)

	total_row = frappe._dict()
	total_row["sales_invoice"] = "Total"
	total_row["qty"] = None
	total_row["avg._selling_rate"] = None
	total_row["valuation_rate"] = None
	total_row["selling_amount"] = totals["selling_amount"]
	total_row["credit_note_total"] = totals["credit_note_total"]
	total_row["selling_total"] = totals["selling_total"]
	total_row["buying_amount"] = totals["buying_amount"]
	total_row["commission_amount"] = totals["commission_amount"]
	total_row["gross_profit"] = totals["gross_profit"]
	total_row["gross_profit_%"] = totals["gross_profit_percent"]
	total_row["gross_profit_%_on_cost"] = totals["gross_profit_percent_on_cost"]

	data.append(total_row)

def get_data_when_not_grouped_by_invoice(gross_profit_data, filters, group_wise_columns, data):
	totals = init_totals()
	
	for src in gross_profit_data.grouped_data:
		row = []
		for col in group_wise_columns.get(scrub(filters.group_by)):
			row.append(src.get(col))

		row.append(filters.currency)

		update_totals(totals, src)

		calculate_gross_profit_percentages(totals)

		data.append(row)

	total_row = [
		'Total', '', '', totals["qty"], '', '', totals["selling_amount"], totals["credit_note_total"],
		totals["selling_total"], totals["buying_amount"], totals["commission_amount"],
		totals["gross_profit"], totals["gross_profit_percent"], totals["gross_profit_percent_on_cost"], ''
	]

	data.append(total_row)

def init_totals():
	return {
		"qty": 0.0,
		"selling_amount": 0.0,
		"credit_note_total": 0.0,
		"selling_total": 0.0,
		"buying_amount": 0.0,
		"commission_amount": 0.0,
		"gross_profit": 0.0,
		"gross_profit_percent": 0.0,
		"gross_profit_percent_on_cost": 0.0
	}


def update_totals(totals, src):
	totals["qty"] += flt(src.qty)
	totals["selling_amount"] += flt(src.base_amount)
	totals["credit_note_total"] += flt(src.credit_note_total)
	totals["selling_total"] += flt(src.selling_total)
	totals["buying_amount"] += flt(src.buying_amount)
	totals["commission_amount"] += flt(src.commission_amount)
	totals["gross_profit"] += flt(src.gross_profit)


def calculate_gross_profit_percentages(totals):
	if totals["selling_total"]:
		totals["gross_profit_percent"] = (totals["gross_profit"] / totals["selling_total"]) * 100
	if totals["buying_amount"]:
		totals["gross_profit_percent_on_cost"] = (totals["gross_profit"] / totals["buying_amount"]) * 100
	

def get_columns(group_wise_columns, filters):
	columns = []
	column_map = frappe._dict(
		{
			"parent": {
				"label": _("Sales Invoice"),
				"fieldname": "parent_invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 120,
			},
			"invoice_or_item": {
				"label": _("Sales Invoice"),
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 120,
			},
			"posting_date": {
				"label": _("Posting Date"),
				"fieldname": "posting_date",
				"fieldtype": "Date",
				"width": 100,
			},
			"posting_time": {
				"label": _("Posting Time"),
				"fieldname": "posting_time",
				"fieldtype": "Data",
				"width": 100,
			},
			"item_code": {
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			},
			"item_name": {
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Data",
				"width": 100,
			},
			"item_group": {
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100,
			},
			"sales_partner_name": {
				"label": _("Sales Partner"),
				"fieldname": "sales_partner_name",
				"fieldtype": "Data",
				"width": 100,
			},
			"brand": {"label": _("Brand"), "fieldtype": "Link", "options": "Brand", "width": 100},
			"description": {
				"label": _("Description"),
				"fieldname": "description",
				"fieldtype": "Data",
				"width": 100,
			},
			"warehouse": {
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 100,
			},
			"qty": {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
			"base_rate": {
				"label": _("Sell Rate"),
				"fieldname": "avg._selling_rate",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"buying_rate": {
				"label": _("Valn Rate"),
				"fieldname": "valuation_rate",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"base_amount": {
				"label": _("Sell Amt"),
				"fieldname": "selling_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"credit_note_total": {
				"label": _("Cr Note"),
				"fieldname": "credit_note_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"selling_total": {
				"label": _("Sell Total"),
				"fieldname": "selling_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"buying_amount": {
				"label": _("Buy Amt"),
				"fieldname": "buying_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"commission_amount": {
				"label": _("Comm Amt"),
				"fieldname": "commission_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
#			"incentive_amount": {
#				"label": _("Incentive Amount"),
#				"fieldname": "incentive_amount",
#				"fieldtype": "Currency",
#				"options": "currency",
#				"width": 100,
#			},
			"gross_profit": {
				"label": _("GP"),
				"fieldname": "gross_profit",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			},
			"gross_profit_percent": {
				"label": _("GP %"),
				"fieldname": "gross_profit_%",
				"fieldtype": "Percent",
				"width": 100,
			},
			"gross_profit_percent_on_cost": {
				"label": _("GP % (Cost)"),
				"fieldname": "gross_profit_%_on_cost",
				"fieldtype": "Percent",
				"width": 120,
			},
			"project": {
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 100,
			},
			"sales_person": {
				"label": _("Sales Person"),
				"fieldname": "sales_person",
				"fieldtype": "Link",
				"options": "Sales Person",
				"width": 100,
			},
			"customer": {
				"label": _("Customer"),
				"fieldname": "customer",
				"fieldtype": "Link",
				"options": "Customer",
				"width": 100,
			},
			"customer_group": {
				"label": _("Customer Group"),
				"fieldname": "customer_group",
				"fieldtype": "Link",
				"options": "Customer Group",
				"width": 100,
			},
			"territory": {
				"label": _("Territory"),
				"fieldname": "territory",
				"fieldtype": "Link",
				"options": "Territory",
				"width": 100,
			},
			"stock_creation_documents": {
				"label": _("Stock Creation Documents(Serialized)"),
				"fieldname": "stock_creation_documents",
				"fieldtype": "Data",
				"width": 400,
			},
		}
	)

	for col in group_wise_columns.get(scrub(filters.group_by)):
		columns.append(column_map.get(col))

	columns.append(
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		}
	)

	return columns


def get_column_names():
	return frappe._dict(
		{
			"invoice_or_item": "sales_invoice",
			"customer": "customer",
			"customer_group": "customer_group",
			"posting_date": "posting_date",
			"item_code": "item_code",
			"item_name": "item_name",
			"item_group": "item_group",
			"sales_partner_name": "sales_partner_name",
			"brand": "brand",
			"description": "description",
			"warehouse": "warehouse",
			"qty": "qty",
			"base_rate": "avg._selling_rate",
			"buying_rate": "valuation_rate",
			"base_amount": "selling_amount",
			"credit_note_total": "credit_note_total",
			"selling_total": "selling_total",
			"buying_amount": "buying_amount",
			"commission_amount": "commission_amount",
#			"incentive_amount": "incentive_amount",
			"gross_profit": "gross_profit",
			"gross_profit_percent": "gross_profit_%",
			"gross_profit_percent_on_cost": "gross_profit_%_on_cost",
			"project": "project",
			"stock_creation_documents": "stock_creation_documents"
		}
	)


class GrossProfitGenerator:
	def __init__(self, filters=None):
		self.sle = {}
		self.data = []
		self.average_buying_rate = {}
		self.filters = frappe._dict(filters)
		self.load_invoice_items()
		self.get_delivery_notes()

		if filters.group_by in ["Invoice", "Default"]:
			self.group_items_by_invoice(filters)

		self.load_product_bundle()
		self.load_non_stock_items()
		self.get_returned_invoice_items()
		self.process()

	def process(self):
		self.grouped = {}
		self.grouped_data = []

		self.currency_precision = cint(frappe.db.get_default("currency_precision")) or 3
		self.float_precision = cint(frappe.db.get_default("float_precision")) or 2

		grouped_by_invoice = True if self.filters.get("group_by") in ["Invoice", "Default"] else False

		if grouped_by_invoice:
			buying_amount = 0
			base_amount = 0

		for row in reversed(self.si_list):
			if self.skip_row(row):
				continue

			row.base_amount = flt(row.base_net_amount, self.currency_precision)

			if "stock_creation_documents" not in row:
				row.stock_creation_documents = self.get_stock_creation_documents(
					row.parent, row.item_code, row.warehouse, row.posting_date, row.item_row
				)

			product_bundles = []
			if row.update_stock:
				product_bundles = self.product_bundles.get(row.parenttype, {}).get(row.parent, frappe._dict())
				
			elif row.dn_detail:
				product_bundles = self.product_bundles.get("Delivery Note", {}).get(
					row.delivery_note, frappe._dict()
				)
				row.item_row = row.dn_detail
				# Update warehouse and base_amount from 'Packed Item' List
				if product_bundles and not row.parent:
					# For Packed Items, row.parent_invoice will be the Bundle name
					product_bundle = product_bundles.get(row.parent_invoice)
					if product_bundle:
						for packed_item in product_bundle:
							if (
								packed_item.get("item_code") == row.item_code
								and packed_item.get("parent_detail_docname") == row.item_row
							):
								row.warehouse = packed_item.warehouse
								row.base_amount = packed_item.base_amount
			# get buying amount
			if row.item_code in product_bundles:
				row.buying_amount = flt(
					self.get_buying_amount_from_product_bundle(row, product_bundles[row.item_code]),
					self.currency_precision,
				)
			else:
				row.buying_amount = flt(self.get_buying_amount(row, row.item_code), self.currency_precision)

			if grouped_by_invoice and row.indent == 0.0:
				row.buying_amount = buying_amount
				row.base_amount = base_amount
				buying_amount = 0
				base_amount = 0

			# get buying rate
			if flt(row.qty):
				row.buying_rate = flt(row.buying_amount / flt(row.qty), self.float_precision)
				row.base_rate = flt(row.base_amount / flt(row.qty), self.float_precision)
			else:
				if self.is_not_invoice_row(row):
					row.buying_rate, row.base_rate = 0.0, 0.0

			if self.is_not_invoice_row(row):
				self.update_return_invoices(row)

			if grouped_by_invoice and row.indent == 1.0:
				buying_amount += row.buying_amount
				base_amount += row.base_amount

			# calculate gross profit
			row.credit_note_total = flt(row.credit_note_total, self.float_precision)
			row.commission_amount = flt(row.commission_amount, self.float_precision)
#			row.incentive_amount = flt(row.incentive_amount, self.float_precision)
			row.selling_total = flt(row.base_amount - row.credit_note_total, self.float_precision)
			row.gross_profit = flt(row.selling_total - row.buying_amount - row.commission_amount, self.currency_precision)
			if row.selling_total:
				row.gross_profit_percent = flt(
					(row.gross_profit / row.selling_total) * 100.0, self.currency_precision
				)
			else:
				row.gross_profit_percent = 0.0
			if row.buying_amount:
				row.gross_profit_percent_on_cost = flt(
					(row.gross_profit / row.buying_amount) * 100.0, self.currency_precision
 				)
			else:
				row.gross_profit_percent_on_cost = 0.0

			# add to grouped
			self.grouped.setdefault(row.get(scrub(self.filters.group_by)), []).append(row)

		if self.grouped:
			self.get_average_rate_based_on_group_by()

	def update_return_invoices(self, row):
		if row.parent in self.returned_invoices and row.item_code in self.returned_invoices[row.parent]:
			returned_item_rows = self.returned_invoices[row.parent][row.item_code]
			for returned_item_row in returned_item_rows:
				# returned_items 'qty' should be stateful
				if returned_item_row.qty != 0:
					if row.qty >= abs(returned_item_row.qty):
						row.qty += returned_item_row.qty
						row.base_amount += flt(returned_item_row.base_amount, self.currency_precision)
						returned_item_row.qty = 0
						returned_item_row.base_amount = 0

					else:
						row.qty = 0
						row.base_amount = 0
						returned_item_row.qty += row.qty
						returned_item_row.base_amount += row.base_amount

			row.buying_amount = flt(flt(row.qty) * flt(row.buying_rate), self.currency_precision)

	def get_average_rate_based_on_group_by(self):
		for key in list(self.grouped):
			if self.filters.get("group_by") in ["Invoice", "Default"]:
				for row in self.grouped[key]:
					if row.indent == 1.0:
						if (
							row.parent in self.returned_invoices
							and row.item_code in self.returned_invoices[row.parent]
						):
							returned_item_rows = self.returned_invoices[row.parent][row.item_code]
							for returned_item_row in returned_item_rows:
								# returned_items 'qty' should be stateful
								if returned_item_row.qty != 0:
									if row.qty >= abs(returned_item_row.qty):
										row.qty += returned_item_row.qty
										returned_item_row.qty = 0
									else:
										row.qty = 0
										returned_item_row.qty += row.qty
								row.base_amount += flt(returned_item_row.base_amount, self.currency_precision)
							row.buying_amount = flt(
								flt(row.qty) * flt(row.buying_rate), self.currency_precision
							)

						if flt(row.qty) or row.base_amount:
							row = self.set_average_rate(row)
							self.grouped_data.append(row)
			else:
				for i, row in enumerate(self.grouped[key]):
					if i == 0:
						new_row = row
					else:
						new_row.qty += flt(row.qty)
						new_row.selling_total += flt(row.selling_total, self.currency_precision)
						new_row.buying_amount += flt(row.buying_amount, self.currency_precision)
						new_row.base_amount += flt(row.base_amount, self.currency_precision)
						new_row.credit_note_total += flt(row.credit_note_total, self.currency_precision)
						new_row.commission_amount += flt(row.commission_amount, self.currency_precision)
#						new_row.incentive_amount += flt(row.incentive_amount, self.currency_precision)
				new_row = self.set_average_rate(new_row)
				self.grouped_data.append(new_row)

	def is_not_invoice_row(self, row):
		return (self.filters.get("group_by") in ["Invoice", "Default"] and row.indent != 0.0) or self.filters.get(
			"group_by"
		) not in ["Invoice", "Default"]

	def set_average_rate(self, new_row):
		self.set_average_gross_profit(new_row)
		new_row.buying_rate = (
			flt(new_row.buying_amount / new_row.qty, self.float_precision) if new_row.qty else 0
		)
		new_row.base_rate = flt(new_row.base_amount / new_row.qty, self.float_precision) if new_row.qty else 0

		return new_row

	def set_average_gross_profit(self, new_row):
		new_row.gross_profit = flt(new_row.selling_total - new_row.buying_amount - new_row.commission_amount, self.currency_precision)
		new_row.gross_profit_percent = (
			flt(((new_row.gross_profit / new_row.selling_total) * 100.0), self.currency_precision)
			if new_row.selling_total
			else 0
		)
		new_row.gross_profit_percent_on_cost = (
			flt(((new_row.gross_profit / new_row.buying_amount) * 100.0), self.currency_precision)
			if new_row.buying_amount
			else 0
		)

	def get_returned_invoice_items(self):
		returned_invoices = frappe.db.sql(
			"""
			select
				si.name, si_item.item_code, si_item.stock_qty as qty, si_item.base_net_amount as base_amount, si.return_against
			from
				`tabSales Invoice` si, `tabSales Invoice Item` si_item
			where
				si.name = si_item.parent
				and si.docstatus = 1
				and si.is_return = 1
		""",
			as_dict=1,
		)

		self.returned_invoices = frappe._dict()
		for inv in returned_invoices:
			self.returned_invoices.setdefault(inv.return_against, frappe._dict()).setdefault(
				inv.item_code, []
			).append(inv)

	def skip_row(self, row):
		if self.filters.get("group_by") not in ["Invoice", "Default"]:
			if not row.get(scrub(self.filters.get("group_by", ""))):
				return True

		return False

	def get_buying_amount_from_product_bundle(self, row, product_bundle):
		buying_amount = 0.0
		for packed_item in product_bundle:
			if packed_item.get("parent_detail_docname") == row.item_row:
				packed_item_row = row.copy()
				packed_item_row.warehouse = packed_item.warehouse
				buying_amount += self.get_buying_amount(packed_item_row, packed_item.item_code)

		return flt(buying_amount, self.currency_precision)

	def calculate_buying_amount_from_sle(self, row, my_sle, parenttype, parent, item_row, item_code):
		for i, sle in enumerate(my_sle):
			# find the stock valution rate from stock ledger entry
			if (
				sle.voucher_type == parenttype
				and parent == sle.voucher_no
				and sle.voucher_detail_no == item_row
			):
				previous_stock_value = len(my_sle) > i + 1 and flt(my_sle[i + 1].stock_value) or 0.0

				if previous_stock_value:
					return abs(previous_stock_value - flt(sle.stock_value)) * flt(row.qty) / abs(flt(sle.qty))
				else:
					return flt(row.qty) * self.get_average_buying_rate(row, item_code)
		return 0.0

	def get_buying_amount(self, row, item_code):
		# IMP NOTE
		# stock_ledger_entries should already be filtered by item_code and warehouse and
		# sorted by posting_date desc, posting_time desc
		if item_code in ("services", "Data Network Point", "Data Network Point 2"):
			return 0.0
		elif item_code == "Data Network Point - Service":
			return flt(row.custom_dnp_expense_total)
		else:
			if item_code in self.non_stock_items and (row.project or row.cost_center):
				# Issue 6089-Get last purchasing rate for non-stock item
				item_rate = self.get_last_purchase_rate(item_code, row)
				return flt(row.qty) * item_rate

			else:
				my_sle = self.get_stock_ledger_entries(item_code, row.warehouse)
				if (row.update_stock or row.dn_detail) and my_sle:
					parenttype, parent = row.parenttype, row.parent
					if row.dn_detail:
						parenttype, parent = "Delivery Note", row.delivery_note

					return self.calculate_buying_amount_from_sle(
						row, my_sle, parenttype, parent, row.item_row, item_code
					)
				elif self.delivery_notes.get((row.parent, row.item_code), None):
					#  check if Invoice has delivery notes
					dn = self.delivery_notes.get((row.parent, row.item_code))
					parenttype, parent, item_row, dn_warehouse = (
						"Delivery Note",
						dn["delivery_note"],
						dn["item_row"],
						dn["warehouse"],
					)
					my_sle = self.get_stock_ledger_entries(item_code, dn_warehouse)
					return self.calculate_buying_amount_from_sle(
						row, my_sle, parenttype, parent, item_row, item_code
					)
				elif row.sales_order and row.so_detail:
					incoming_amount = self.get_buying_amount_from_so_dn(row.sales_order, row.so_detail, item_code)

					if incoming_amount:
						return flt(row.qty) * incoming_amount
				else:
					return flt(row.qty) * self.get_average_buying_rate(row, item_code)

			return flt(row.qty) * self.get_average_buying_rate(row, item_code)

	def get_buying_amount_from_so_dn(self, sales_order, so_detail, item_code):
		from frappe.query_builder.functions import Avg

		delivery_note_item = frappe.qb.DocType("Delivery Note Item")
		query = (
			frappe.qb.from_(delivery_note_item)
			.select(Avg(delivery_note_item.incoming_rate))
			.where(delivery_note_item.docstatus == 1)
			.where(delivery_note_item.item_code == item_code)
			.where(delivery_note_item.against_sales_order == sales_order)
			.where(delivery_note_item.so_detail == so_detail)
			.groupby(delivery_note_item.item_code)
		)
		incoming_amount = query.run()
		return flt(incoming_amount[0][0]) if incoming_amount else 0

	def get_average_buying_rate(self, row, item_code):
		args = row
		if item_code not in self.average_buying_rate:
			args.update(
				{
					"voucher_type": row.parenttype,
					"voucher_no": row.parent,
					"allow_zero_valuation": True,
					"company": self.filters.company,
				}
			)

			if row.serial_and_batch_bundle:
				args.update({"serial_and_batch_bundle": row.serial_and_batch_bundle})

			average_buying_rate = get_incoming_rate(args)
			self.average_buying_rate[item_code] = flt(average_buying_rate)

		return self.average_buying_rate[item_code]

	def get_last_purchase_rate(self, item_code, row):
		purchase_invoice = frappe.qb.DocType("Purchase Invoice")
		purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

		query = (
			frappe.qb.from_(purchase_invoice_item)
			.inner_join(purchase_invoice)
			.on(purchase_invoice.name == purchase_invoice_item.parent)
			.select(
				purchase_invoice_item.base_rate / purchase_invoice_item.conversion_factor,
			)
			.where(purchase_invoice.docstatus == 1)
			.where(purchase_invoice.posting_date <= self.filters.to_date)
			.where(purchase_invoice_item.item_code == item_code)
			.where(purchase_invoice.is_return == 0)
			.where(purchase_invoice_item.parenttype == "Purchase Invoice")
		)

		if row.project:
			query = query.where(purchase_invoice_item.project == row.project)

		if row.cost_center:
			query = query.where(purchase_invoice_item.cost_center == row.cost_center)

		query = query.orderby(purchase_invoice.posting_date, order=frappe.qb.desc).limit(1)
		last_purchase_rate = query.run()

		return flt(last_purchase_rate[0][0]) if last_purchase_rate else 0


	def load_invoice_items(self):
		conditions = ""
		if self.filters.company:
			conditions += " and `tabSales Invoice`.company = %(company)s"
		if self.filters.from_date:
			conditions += " and posting_date >= %(from_date)s"
		if self.filters.to_date:
			conditions += " and posting_date <= %(to_date)s"

		conditions += " and (is_return = 0 or (is_return=1 and return_against is null))"

		if self.filters.item_group:
			item_groups_list = ', '.join(f"'{group}'" for group in self.filters.item_group)
			conditions += f" and item.item_group in ({item_groups_list})"

		if self.filters.sales_person:
			conditions += """
				and exists(select 1
							from `tabSales Team` st
							where st.parent = `tabSales Invoice`.name
							and   st.sales_person = %(sales_person)s)
			"""

		if self.filters.get("sales_invoice"):
			conditions += " and `tabSales Invoice`.name = %(sales_invoice)s"

		if self.filters.get("item_code"):
			conditions += " and `tabSales Invoice Item`.item_code = %(item_code)s"

		if self.filters.get("warehouse"):
			warehouse_details = frappe.db.get_value(
				"Warehouse", self.filters.get("warehouse"), ["lft", "rgt"], as_dict=1
			)
			if warehouse_details:
				conditions += f" and `tabSales Invoice Item`.warehouse in (select name from `tabWarehouse` wh where wh.lft >= {warehouse_details.lft} and wh.rgt <= {warehouse_details.rgt} and warehouse = wh.name)"

		rebate_account = frappe.get_cached_value("Account", {"account_name": "Credit Notes (Rebate Given)"}, "name")
		custom_dnp_expense_field = (
			"`tabSales Invoice`.custom_dnp_expense_total as custom_dnp_expense_total,"
			if frappe.db.has_column("Sales Invoice", "custom_dnp_expense_total")
			else "0 as custom_dnp_expense_total,"
		)

		self.si_list = frappe.db.sql(
			"""
			select
				`tabSales Invoice Item`.parenttype, `tabSales Invoice Item`.parent,
				`tabSales Invoice`.posting_date, `tabSales Invoice`.posting_time,
				`tabSales Invoice`.project, `tabSales Invoice`.update_stock,
				`tabSales Invoice`.customer, `tabSales Invoice`.customer_group,
				`tabSales Invoice`.territory, `tabSales Invoice Item`.item_code,
				`tabSales Invoice`.base_net_total as "invoice_base_net_total",
				`tabSales Invoice Item`.item_name, `tabSales Invoice Item`.description,
				`tabSales Invoice Item`.warehouse, `tabSales Invoice Item`.item_group,
				`tabSales Partner Details`.sales_partner_name, {custom_dnp_expense_field}
				`tabSales Invoice Item`.brand, `tabSales Invoice Item`.so_detail,
				`tabSales Invoice Item`.sales_order, `tabSales Invoice Item`.dn_detail,
				`tabSales Invoice Item`.delivery_note, `tabSales Invoice Item`.stock_qty as qty,
				`tabSales Invoice Item`.base_net_rate, `tabSales Invoice Item`.base_net_amount,
				`tabSales Invoice Item`.name as "item_row", `tabSales Invoice`.is_return,
				`tabSales Invoice Item`.cost_center, `tabSales Invoice Item`.serial_and_batch_bundle,
				(
					SELECT `tabSales Partner Details`.commission_amount
					FROM `tabSales Partner Details`
					WHERE `tabSales Partner Details`.parent = `tabSales Invoice Item`.parent
					AND `tabSales Partner Details`.item_group = `tabSales Invoice Item`.item_group
					LIMIT 1
					) * `tabSales Invoice Item`.base_net_amount / (
					SELECT SUM(`tabSales Invoice Item`.base_net_amount)
					FROM `tabSales Invoice Item`
					WHERE `tabSales Invoice Item`.parent = `tabSales Invoice`.name
					AND `tabSales Invoice Item`.item_group = `tabSales Partner Details`.item_group
					AND `tabSales Invoice Item`.docstatus = 1
					) AS commission_amount,
				(ifnull(sum(`tabSales Team`.incentives), 0) / `tabSales Invoice`.base_net_total) * `tabSales Invoice Item`.base_net_amount as incentive_amount,
				(
					select
						sum(`tabJournal Entry Account`.debit_in_account_currency)
					from
						`tabJournal Entry Account`
					where
						`tabJournal Entry Account`.parent in (
							select
								`tabJournal Entry Account`.parent
							from
								`tabJournal Entry Account`
							where
								`tabJournal Entry Account`.reference_name = `tabSales Invoice`.name
								and `tabJournal Entry Account`.docstatus = 1
						)
						and `tabJournal Entry Account`.account = '{rebate_account}'
						and `tabJournal Entry Account`.docstatus = 1
				) * (`tabSales Invoice Item`.base_net_amount / `tabSales Invoice`.base_net_total) as credit_note_total
			from
				`tabSales Invoice` inner join `tabSales Invoice Item`
					on `tabSales Invoice Item`.parent = `tabSales Invoice`.name
				join `tabItem` item on item.name = `tabSales Invoice Item`.item_code
				left join `tabSales Team` on `tabSales Team`.parent = `tabSales Invoice`.name
				left join `tabSales Partner Details` on `tabSales Partner Details`.parent = `tabSales Invoice`.name
				and `tabSales Partner Details`.item_group = `tabSales Invoice Item`.item_group
			where
				`tabSales Invoice`.docstatus=1 and `tabSales Invoice`.is_opening!='Yes' {conditions} {match_cond}
			group by
				`tabSales Invoice Item`.name,
				`tabSales Invoice`.name
			order by
				`tabSales Invoice`.posting_date desc, `tabSales Invoice`.posting_time desc""".format(
				conditions=conditions,
				match_cond=get_match_cond("Sales Invoice"),
				rebate_account=rebate_account,
				custom_dnp_expense_field=custom_dnp_expense_field,
			),
			self.filters,
			as_dict=1,
		)

		stock_creation_doc = (
			self.filters.get("stock_creation_document") or self.filters.get("stock_creation_documents")
		)
		if stock_creation_doc:
			stock_creation_doc = stock_creation_doc.strip().lower()
			filtered_si_list = []
			for row in self.si_list:
				docs = self.get_stock_creation_documents(
					row.parent, row.item_code, row.warehouse, row.posting_date, row.item_row
				)
				row.stock_creation_documents = docs
				if docs and stock_creation_doc in docs.lower():
					filtered_si_list.append(row)
			self.si_list = filtered_si_list

	def get_delivery_notes(self):
		self.delivery_notes = frappe._dict({})
		if self.si_list:
			invoices = [x.parent for x in self.si_list]
			dni = qb.DocType("Delivery Note Item")
			delivery_notes = (
				qb.from_(dni)
				.select(
					dni.against_sales_invoice.as_("sales_invoice"),
					dni.item_code,
					dni.warehouse,
					dni.parent.as_("delivery_note"),
					dni.name.as_("item_row"),
				)
				.where((dni.docstatus == 1) & (dni.against_sales_invoice.isin(invoices)))
				.groupby(dni.against_sales_invoice, dni.item_code)
				.orderby(dni.creation, order=Order.desc)
				.run(as_dict=True)
			)

			for entry in delivery_notes:
				self.delivery_notes[(entry.sales_invoice, entry.item_code)] = entry

	def group_items_by_invoice(self, filters):
		"""
		Turns list of Sales Invoice Items to a tree of Sales Invoices with their Items as children.
		"""
		grouped = OrderedDict()

		for row in self.si_list:
			invoice_row = self.get_invoice_row(row, filters)

			credit_note_total = invoice_row.get("credit_note_total", 0)
			invoice_total = invoice_row.get("base_net_amount", 0)

			credit_note_for_item = 0
			if invoice_total:
				credit_note_for_item = (row.base_net_amount / invoice_total) * credit_note_total

			invoice_or_item = row.item_code if filters.group_by == "Invoice" else row.parent

			# initialize list with a header row for each new parent
			grouped.setdefault(row.parent, [invoice_row]).append(
				row.update(
					{"indent": 1.0, "parent_invoice": row.parent, "invoice_or_item": invoice_or_item,
					"credit_note_total": credit_note_for_item, "selling_total": row.base_net_amount - credit_note_for_item
					}
				)  # descendant rows will have indent: 1.0 or greater
			)

			# if item is a bundle, add it's components as seperate rows
			if frappe.db.exists("Product Bundle", row.item_code):
				bundled_items = self.get_bundle_items(row)
				for x in bundled_items:
					bundle_item = self.get_bundle_item_row(row, x)
					grouped.get(row.parent).append(bundle_item)

		self.si_list.clear()
		for items in grouped.values():
			self.si_list.extend(items)

	def get_invoice_row(self, row, filters):
		# header row format

		rebate_account = frappe.get_cached_value("Account", {"account_name": "Credit Notes (Rebate Given)"}, "name")

		credit_note_total = frappe.db.sql(
			"""
			select
				sum(`tabJournal Entry Account`.debit_in_account_currency)
			from
				`tabJournal Entry Account`
			where
				`tabJournal Entry Account`.parent in (
					select
						`tabJournal Entry Account`.parent
					from
						`tabJournal Entry Account`
					where
						`tabJournal Entry Account`.reference_name = %s
						and `tabJournal Entry Account`.docstatus = 1
				)
				and `tabJournal Entry Account`.account = %s
				and `tabJournal Entry Account`.docstatus = 1
			""", (row.parent, rebate_account)
		)

		credit_note_total = credit_note_total[0][0] or 0 if credit_note_total else 0

#		total_incentive_amount = frappe.db.sql("""
#    	SELECT SUM(incentives)
#    		FROM `tabSales Team`
#    		WHERE parent = %s
#		""", (row.parent,), as_dict=False)[0][0]

		total_commission_amount = frappe.db.sql("""
			SELECT SUM(commission_amount)
			FROM `tabSales Partner Details`
    		WHERE parent = %s
		""", (row.parent,))[0][0] or 0


		return frappe._dict(
			{
				"parent_invoice": "",
				"indent": 0.0,
				"invoice_or_item": row.parent,
				"parent": None,
				"posting_date": row.posting_date,
				"posting_time": row.posting_time,
				"project": row.project,
				"update_stock": row.update_stock,
				"customer": row.customer,
				"customer_group": row.customer_group,
				"item_code": None,
				"item_name": None,
				"description": None,
				"warehouse": None,
				"item_group": None,
				"sales_partner_name": None,
#				"brand": None,
				"dn_detail": None,
				"delivery_note": None,
				"qty": None,
				"item_row": None,
				"is_return": row.is_return,
				"cost_center": row.cost_center,
				"base_net_amount": row.invoice_base_net_total,
				"credit_note_total": credit_note_total,
				"selling_total": row.invoice_base_net_total - credit_note_total,
				"commission_amount": total_commission_amount,
#				"incentive_amount": total_incentive_amount
			}
		)

	def get_bundle_items(self, product_bundle):
		return frappe.get_all(
			"Product Bundle Item", filters={"parent": product_bundle.item_code}, fields=["item_code", "qty"]
		)

	def get_bundle_item_row(self, product_bundle, item):
		item_name, description, item_group, brand = self.get_bundle_item_details(item.item_code)

#		total_incentive_amount = frappe.db.sql("""
#    	SELECT SUM(incentives)
#    		FROM `tabSales Team`
#    		WHERE parent = %s
#		""", (product_bundle.parent,), as_dict=False)[0][0]

		total_commission_amount = frappe.db.sql("""
		SELECT SUM(commission_amount)
			FROM `tabSales Partner Details`
			WHERE parent = %s
		""", (product_bundle.parent,))[0][0] or 0

		return frappe._dict(
			{
				"parent_invoice": product_bundle.item_code,
				"indent": product_bundle.indent + 1,
				"parent": None,
				"invoice_or_item": item.item_code,
				"posting_date": product_bundle.posting_date,
				"posting_time": product_bundle.posting_time,
				"project": product_bundle.project,
				"customer": product_bundle.customer,
				"customer_group": product_bundle.customer_group,
				"item_code": item.item_code,
				"item_name": item_name,
				"description": description,
				"warehouse": product_bundle.warehouse,
				"item_group": item_group,
				"brand": brand,
				"dn_detail": product_bundle.dn_detail,
				"delivery_note": product_bundle.delivery_note,
				"qty": (flt(product_bundle.qty) * flt(item.qty)),
				"item_row": None,
				"is_return": product_bundle.is_return,
				"cost_center": product_bundle.cost_center,
				"commission_amount": total_commission_amount,
#				"incentive_amount": total_incentive_amount,
			}
		)

	def get_bundle_item_details(self, item_code):
		return frappe.db.get_value("Item", item_code, ["item_name", "description", "item_group", "brand"])

	def get_stock_ledger_entries(self, item_code, warehouse):
		if item_code and warehouse:
			if (item_code, warehouse) not in self.sle:
				sle = qb.DocType("Stock Ledger Entry")
				res = (
					qb.from_(sle)
					.select(
						sle.item_code,
						sle.voucher_type,
						sle.voucher_no,
						sle.voucher_detail_no,
						sle.stock_value,
						sle.warehouse,
						sle.actual_qty.as_("qty"),
					)
					.where(
						(sle.company == self.filters.company)
						& (sle.item_code == item_code)
						& (sle.warehouse == warehouse)
						& (sle.is_cancelled == 0)
					)
					.orderby(sle.item_code)
					.orderby(sle.warehouse, sle.posting_datetime, sle.creation, order=Order.desc)
					.run(as_dict=True)
				)

				self.sle[(item_code, warehouse)] = res

			return self.sle[(item_code, warehouse)]
		return []

	def load_product_bundle(self):
		self.product_bundles = {}

		pki = qb.DocType("Packed Item")

		pki_query = (
			frappe.qb.from_(pki)
			.select(
				pki.parenttype,
				pki.parent,
				pki.parent_item,
				pki.item_code,
				pki.warehouse,
				(-1 * pki.qty).as_("total_qty"),
				pki.rate,
				(pki.rate * pki.qty).as_("base_amount"),
				pki.parent_detail_docname,
			)
			.where(pki.docstatus == 1)
		)

		for d in pki_query.run(as_dict=True):
			self.product_bundles.setdefault(d.parenttype, frappe._dict()).setdefault(
				d.parent, frappe._dict()
			).setdefault(d.parent_item, []).append(d)

	def load_non_stock_items(self):
		self.non_stock_items = frappe.db.sql_list(
			"""select name from tabItem
			where is_stock_item=0"""
		)

	def get_stock_creation_documents(self, sales_invoice, item_code, warehouse, posting_date, item_row):
		if not (item_code and warehouse and posting_date):
			return ""

		row_related = []
		si_items = frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": sales_invoice, "item_code": item_code, "warehouse": warehouse, "name": item_row},
			fields=["serial_and_batch_bundle", "delivery_note"]
		)

		for si_item in si_items:
			bundle = si_item.serial_and_batch_bundle
			if bundle:
				related = self.get_creation_docs_from_bundle(bundle)
				row_related.append(", ".join(f"{doc} ({count})" for doc, count in sorted(related.items())))
			elif si_item.delivery_note:
				dn_items = frappe.get_all(
					"Delivery Note Item",
					filters={"parent": si_item.delivery_note, "item_code": item_code, "warehouse": warehouse,},
					fields=["serial_and_batch_bundle"]
				)
				for dn in dn_items:
					if dn.serial_and_batch_bundle:
						related = self.get_creation_docs_from_bundle(dn.serial_and_batch_bundle)
						row_related.append(", ".join(f"{doc} ({count})" for doc, count in sorted(related.items())))
			else:
				dn_items = frappe.get_all(
					"Delivery Note Item",
					filters={"against_sales_invoice": sales_invoice, "item_code": item_code, "warehouse": warehouse},
					fields=["serial_and_batch_bundle"]
				)
				for dn in dn_items:
					if dn.serial_and_batch_bundle:
						related = self.get_creation_docs_from_bundle(dn.serial_and_batch_bundle)
						row_related.append(", ".join(f"{doc} ({count})" for doc, count in sorted(related.items())))

		return "; ".join(row_related) if row_related else None

	def get_creation_docs_from_bundle(self, bundle):
		if not hasattr(self, "_bundle_creation_docs"):
			self._bundle_creation_docs = {}
		if bundle in self._bundle_creation_docs:
			return self._bundle_creation_docs[bundle]

		related = {}
		serials = frappe.db.sql("""
			SELECT sn.purchase_document_no
			FROM `tabSerial and Batch Entry` sbe
			LEFT JOIN `tabSerial No` sn ON sn.name = sbe.serial_no
			WHERE sbe.parent = %s AND sn.purchase_document_no IS NOT NULL
		""", (bundle,), as_dict=True)

		for row in serials:
			related[row.purchase_document_no] = related.get(row.purchase_document_no, 0) + 1

		self._bundle_creation_docs[bundle] = related
		return related




@frappe.whitelist()
def get_stock_creation_documents_list(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None, company=None):
	"""Custom query for Stock Creation Document filter in GP Report.

	Returns list of dicts with value, label, description for Frappe Autocomplete control.
	"""
	import json as _json

	if not txt:
		txt = ""

	if not company and filters:
		if isinstance(filters, str):
			filters = _json.loads(filters)
		if isinstance(filters, dict):
			company = filters.get("company")

	params = {"txt": f"%{txt}%", "limit": cint(page_len) or 20}
	conditions = ""
	if company:
		conditions += " AND (sn.company = %(company)s OR sn.company IS NULL OR sn.company = '')"
		params["company"] = company

	rows = frappe.db.sql(
		f"""
			SELECT DISTINCT sn.purchase_document_no
			FROM `tabSerial No` sn
			WHERE sn.purchase_document_no IS NOT NULL
				AND sn.purchase_document_no != ''
				AND sn.purchase_document_no LIKE %(txt)s
				{conditions}
			ORDER BY sn.modified DESC
			LIMIT %(limit)s
		""",
		params,
	)

	_prefix_map = {
		"PINV": "Purchase Invoice",
		"PR":   "Purchase Receipt",
		"SE":   "Stock Entry",
		"DN":   "Delivery Note",
		"SINV": "Sales Invoice",
	}

	def _doc_type_label(name):
		for part in name.split("-"):
			if part.upper() in _prefix_map:
				return _prefix_map[part.upper()]
		return ""

	return [
		{"value": row[0], "label": row[0], "description": _doc_type_label(row[0])}
		for row in rows
	]
