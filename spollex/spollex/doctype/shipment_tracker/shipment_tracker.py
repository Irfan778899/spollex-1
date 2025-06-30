# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import getdate

class ShipmentTracker(Document):
	def validate(self):
		self.set_status()
		self.validate_collection_qty()
		self.set_balance_qty()

	def set_status(self):
		today_date = getdate()
		actual_received_date = getdate(self.actual_received_date) if self.actual_received_date else None
		etd = getdate(self.etd) if self.etd else None
		collection_date = getdate(self.collection_date) if self.collection_date else None

		if actual_received_date and actual_received_date <= today_date:
			self.status = "Received"
		elif etd and etd <= today_date:
			self.status = "In Transit"
		elif collection_date and collection_date <= today_date:
			self.status = "Pickup Scheduled"
		else:
			self.status = "Open"

	def validate_collection_qty(self):
		for item in self.items:
			if item.pending_ordered_qty and item.collection_qty:
				if item.collection_qty > item.pending_ordered_qty:
					frappe.throw(f"Collection Qty ({item.collection_qty}) cannot be greater than Pending Ordered Qty ({item.pending_ordered_qty}) for item {item.item_code}.")

	def set_balance_qty(self):
		for item in self.items:
			if item.pending_ordered_qty and item.collection_qty:
				item.balance_qty = item.pending_ordered_qty - item.collection_qty - item.approved_qty
			else:
				item.balance_qty = 0

@frappe.whitelist()
def make_shipment_tracker(source_name, target_doc=None):
	po_items = frappe.get_all(
		"Purchase Order Item",
		filters={"parent": source_name},
		fields=["name", "item_code", "qty"]
	)

	has_pending = False

	for po_item in po_items:
		# Get total qty already collected for this item
		already_shipped = frappe.db.sql("""
			SELECT SUM(sti.collection_qty)
			FROM `tabShipment Tracker Item` sti
			JOIN `tabShipment Tracker` st ON sti.parent = st.name
			WHERE st.docstatus < 2
			  AND st.purchase_order = %s
			  AND sti.po_detail = %s
		""", (source_name, po_item.name))[0][0] or 0

		if po_item.qty - already_shipped > 0:
			has_pending = True
			break

	if not has_pending:
		frappe.throw("All items in this Purchase Order have already been collected in previous Shipment Trackers.")

	return get_mapped_doc(
		"Purchase Order",  # Source doctype
		source_name,       # Source name (docname of Purchase Order)
		{
			"Purchase Order": {
				"doctype": "Shipment Tracker",  # Target doctype
				"field_map": {
					"name": "purchase_order", 
					"supplier": "supplier",
				}
			},
			"Purchase Order Item": {
				"doctype": "Shipment Tracker Item",  # Target doctype
				"field_map": {
					"item_code": "item_code", 
					"description": "description",
					"name": "po_detail"
				}
			}
		},
		target_doc,
		postprocess=set_pending_qty
	)

def set_pending_qty(source_doc, target_doc):
	items_to_keep = []

	for item in target_doc.items:
		if item.item_code and item.po_detail:
			# Get total qty already shipped from Shipment Tracker for this PO and item
			already_shipped = frappe.db.sql("""
				SELECT SUM(sti.collection_qty)
				FROM `tabShipment Tracker Item` sti
				JOIN `tabShipment Tracker` st ON sti.parent = st.name
				WHERE st.docstatus < 2
				AND st.purchase_order = %s
				AND sti.po_detail = %s
			""", (source_doc.name, item.po_detail))[0][0] or 0

			# Get ordered qty from Purchase Order Item
			po_item_qty = frappe.db.get_value("Purchase Order Item", item.po_detail, "qty") or 0

			pending_qty = po_item_qty - already_shipped

			if pending_qty > 0:
				item.pending_ordered_qty = pending_qty
				items_to_keep.append(item)
	target_doc.items = items_to_keep
