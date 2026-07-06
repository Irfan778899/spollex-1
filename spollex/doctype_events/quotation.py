# Copyright (c) 2026, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def validate_subscription_details(doc, method=None):
    target_dt = "Sales Order" if getattr(doc, "custom_export", 0) else "Sales Invoice"
    doc.custom_old_doctype = target_dt

    is_new = getattr(doc, "custom_is_new_subscription", 0)
    if doc.custom_subscription_type in ["AMC", "License"] and not is_new and not doc.custom_old_invoice:
        label = _("Old Proforma Invoice") if getattr(doc, "custom_export", 0) else _("Old Invoice")
        frappe.throw(_("{0} is mandatory when Subscription Type is {1}").format(label, doc.custom_subscription_type))
