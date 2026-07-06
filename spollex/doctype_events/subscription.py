# Copyright (c) 2026, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def validate_subscription_details(doc, method=None):
	target_dt = "Sales Order" if doc.get("custom_export") else "Sales Invoice"
	doc.custom_old_doctype = target_dt

	is_new = doc.get("custom_is_new_subscription")
	if doc.custom_subscription_type in ["AMC", "License"] and not is_new and not doc.get("custom_old_invoice"):
		label = _("Old Proforma Invoice") if doc.get("custom_export") else _("Old Invoice")
		frappe.throw(
			_("{0} is mandatory when Subscription Type is {1}").format(label, doc.custom_subscription_type)
		)

	_sync_subscription_item_amounts(doc)
	_validate_subscription_item_dates(doc)


def _sync_subscription_item_amounts(doc):
	item_codes_in_doc = {item.item_code for item in (doc.items or [])}
	item_amount_map = {}
	for item in doc.items or []:
		if item.item_code:
			item_amount_map[item.item_code] = item_amount_map.get(item.item_code, 0) + (item.amount or 0)

	for row in doc.custom_subscription_items or []:
		if not row.item_code:
			continue
		if row.item_code not in item_codes_in_doc:
			frappe.throw(
				_("Row #{0}: Item {1} in Subscription Items is not present in the Items table.").format(
					row.idx, row.item_code
				)
			)
		row.amount = item_amount_map.get(row.item_code, 0)


def _validate_subscription_item_dates(doc):
	for row in doc.custom_subscription_items or []:
		if row.from_date and row.to_date and getdate(row.from_date) > getdate(row.to_date):
			frappe.throw(
				_("Row #{0}: From Date cannot be after To Date in Subscription Items.").format(row.idx)
			)


def update_renewal_invoice_status(doc, method=None, is_export=False):
	old_invoice = doc.get("custom_old_invoice")
	if not old_invoice or bool(doc.get("custom_export")) != is_export:
		return

	is_renewed = 1 if method == "on_submit" else 0
	target_dt = doc.get("custom_old_doctype") or ("Sales Order" if is_export else "Sales Invoice")
	if frappe.db.exists(target_dt, old_invoice):
		frappe.db.set_value(target_dt, old_invoice, "custom_renewed", is_renewed)
