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
        ["name", "total_visits", "completed_visits", "balance_visits"],
        as_dict=True
    )

    if not visit_row:
        frappe.throw(
            _("The contract does not cover this Visit Type: {0}.")
            .format(doc.custom_visit_type)
        )

    completed = visit_row.completed_visits or 0
    balance = visit_row.balance_visits or 0

    if method == "on_submit":
        if balance <= 0:
            frappe.throw(
                _("Cannot submit Maintenance Visit as there are no remaining visits for Visit Type: {0}")
                .format(doc.custom_visit_type)
            )
        else:
            completed = visit_row.completed_visits + 1
            balance = visit_row.balance_visits - 1
    elif method == "on_cancel":
        completed -= 1
        balance += 1
    
    frappe.db.set_value(
        "Contract Visit Detail",
        visit_row.name,
        {
            "completed_visits": completed,
            "balance_visits": balance
        }
    )
    