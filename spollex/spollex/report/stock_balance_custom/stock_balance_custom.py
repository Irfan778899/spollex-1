# Copyright (c) 2026, 4C Solutions and Contributors
# License: GNU General Public License v3. See license.txt

import json
from typing import Any

import frappe
from frappe.query_builder import Order
from frappe.query_builder.functions import Count
from frappe.utils.nestedset import get_descendants_of

from erpnext.stock.report.stock_balance.stock_balance import (
	StockBalanceFilter,
	StockBalanceReport,
)


def execute(filters: StockBalanceFilter | dict[str, Any] | None = None):
	return StockBalanceCustomReport(filters).run()


def parse_filter_list(val: Any) -> list[str]:
	"""Parse a filter value into a list of non-empty strings.

	Handles JSON lists (from frontend MultiSelectList), lists/tuples/sets, and single strings.
	"""
	if not val:
		return []
	if isinstance(val, str):
		try:
			parsed = json.loads(val)
			if isinstance(parsed, list):
				return [str(x) for x in parsed if x]
		except Exception:
			pass
		return [val]
	if isinstance(val, (list, tuple, set)):
		return [str(x) for x in val if x]
	return [str(val)]


def get_item_groups_with_descendants(item_groups: Any) -> list[str]:
	"""Return the given item groups and all their descendants in the tree hierarchy."""
	groups = parse_filter_list(item_groups)
	if not groups:
		return []
	all_groups = set()
	for ig in groups:
		if not ig:
			continue
		all_groups.add(ig)
		if descendants := get_descendants_of("Item Group", ig, ignore_permissions=True):
			all_groups.update(descendants)
	return list(all_groups)


class StockBalanceCustomReport(StockBalanceReport):
	"""Custom Stock Balance Report subclassing ERPNext's standard StockBalanceReport

	Enhances standard functionality by supporting multiselect Item Group filters with descendant traversal.
	"""

	def __init__(self, filters: StockBalanceFilter | dict[str, Any] | None = None) -> None:
		# Ensure self.filters is a frappe._dict for consistent attribute & dict-style access
		super().__init__(frappe._dict(filters or {}))

	def prepare_stock_reco_voucher_wise_count(self) -> None:
		self.stock_reco_voucher_wise_count = frappe._dict()

		doctype = frappe.qb.DocType("Stock Ledger Entry")
		item = frappe.qb.DocType("Item")

		query = (
			frappe.qb.from_(doctype)
			.inner_join(item)
			.on(doctype.item_code == item.name)
			.select(doctype.voucher_detail_no, Count(doctype.name).as_("count"))
			.where(
				(doctype.voucher_type == "Stock Reconciliation")
				& (doctype.docstatus < 2)
				& (doctype.is_cancelled == 0)
				& (item.has_serial_no == 1)
			)
			.groupby(doctype.voucher_detail_no)
		)

		if items := self.filters.get("item_code"):
			items = parse_filter_list(items)
			if items:
				query = query.where(item.name.isin(items))

		if self.filters.get("item_group"):
			children = get_item_groups_with_descendants(self.filters.get("item_group"))
			if children:
				query = query.where(item.item_group.isin(children))

		if warehouses := self.filters.get("warehouse"):
			warehouses = parse_filter_list(warehouses)
			children = []
			for warehouse in warehouses:
				children.append(warehouse)
				if warehouse_children := get_descendants_of("Warehouse", warehouse, ignore_permissions=True):
					children.extend(warehouse_children)

			if children:
				query = query.where(doctype.warehouse.isin(children))

		data = query.run(as_dict=True)
		if not data:
			return

		for row in data:
			if row.count != 1:
				continue

			sr_item = frappe.db.get_value(
				"Stock Reconciliation Item", row.voucher_detail_no, ["current_qty", "qty"], as_dict=True
			)

			if sr_item and sr_item.qty and sr_item.current_qty:
				self.stock_reco_voucher_wise_count[row.voucher_detail_no] = sr_item.current_qty

	def get_closing_balance(self) -> list[dict[str, Any]]:
		if self.filters.get("ignore_closing_balance"):
			return []

		table = frappe.qb.DocType("Closing Stock Balance")

		query = (
			frappe.qb.from_(table)
			.select(table.name, table.to_date)
			.where(
				(table.docstatus == 1)
				& (table.company == self.filters.get("company"))
				& (table.to_date <= self.from_date)
				& (table.status == "Completed")
			)
			.orderby(table.to_date, order=Order.desc)
			.limit(1)
		)

		for fieldname in ["warehouse", "item_code", "item_group", "warehouse_type"]:
			if value := self.filters.get(fieldname):
				if fieldname == "item_group":
					groups = parse_filter_list(value)
					if groups:
						query = query.where(table[fieldname].isin(groups))
				elif isinstance(value, (list, tuple, set)):
					query = query.where(table[fieldname].isin(list(value)))
				else:
					query = query.where(table[fieldname] == value)

		return query.run(as_dict=True)

	def apply_items_filters(self, query, item_table):
		if item_group := self.filters.get("item_group"):
			children = get_item_groups_with_descendants(item_group)
			if children:
				query = query.where(item_table.item_group.isin(children))

		if item_codes := self.filters.get("item_code"):
			item_codes = parse_filter_list(item_codes)
			if item_codes:
				query = query.where(item_table.name.isin(item_codes))

		if brand := self.filters.get("brand"):
			query = query.where(item_table.brand == brand)

		return query
