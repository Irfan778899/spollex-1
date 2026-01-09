# Copyright (c) 2026, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def update_contract_visits(doc, method=None):
    if not doc.custom_contract_id:
        return

    visit_row = frappe.db.get_value(
        "Contract Visit Detail",
        {
            "parent": doc.custom_contract_id,
            "visit_type": doc.custom_visit_type,
            "parenttype": "Contract"
        },
        ["name", "total_visits", "completed_visits"],
        as_dict=True
    )

    if not visit_row:
        return

    completed = visit_row.completed_visits or 0
    total = visit_row.total_visits or 0

    if completed >= total:
        frappe.throw(
            _("No remaining visits available for Visit Type: {0}")
            .format(doc.custom_visit_type)
        )

    completed += 1
    balance = total - completed

    frappe.db.set_value(
        "Contract Visit Detail",
        visit_row.name,
        {
            "completed_visits": completed,
            "balance_visits": balance
        }
    )

def revert_contract_visits(doc, method=None):
    if not doc.custom_contract_id:
        return

    visit_row = frappe.db.get_value(
        "Contract Visit Detail",
        {
            "parent": doc.custom_contract_id,
            "visit_type": doc.custom_visit_type,
            "parenttype": "Contract"
        },
        ["name", "total_visits", "completed_visits"],
        as_dict=True
    )

    if not visit_row:
        return

    completed = visit_row.completed_visits or 0

    if completed <= 0:
        return

    completed -= 1
    balance = visit_row.total_visits - completed

    frappe.db.set_value(
        "Contract Visit Detail",
        visit_row.name,
        {
            "completed_visits": completed,
            "balance_visits": balance
        }
    )

