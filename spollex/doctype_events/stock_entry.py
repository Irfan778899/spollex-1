# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

import frappe

@frappe.whitelist()
def create_journal_entry_on_submit(doc, method):
    for row in doc.additional_costs:
        if row.custom_supplier:
            create_journal_entry(doc, row)

def create_journal_entry(doc, row):
    company = doc.company
    je = frappe.new_doc('Journal Entry')
    je.voucher_type = 'Journal Entry'
    je.posting_date = frappe.utils.nowdate()
    je.bill_no = doc.name

    credit_account = frappe.get_cached_value("Company", company, "default_payable_account")
    if not credit_account:
        frappe.throw(f"Default Payable Account is not set for company {company}")
 
    je.append('accounts',
        {
        'account': credit_account,
        "party_type": "Supplier",
        "party": row.custom_supplier,
        'debit_in_account_currency': 0,
        'credit_in_account_currency': row.amount,
        }
    )

    je.append('accounts',
        {
        'account': row.expense_account,
        "party_type": "",
        "party": "",
        'debit_in_account_currency': row.amount,
        'credit_in_account_currency': 0,
        }
    )

    je.save()
    je.submit()

@frappe.whitelist()
def cancel_journal_entry_on_cancel(doc, method):
    journal_entries = frappe.get_all('Journal Entry', filters={'bill_no': doc.name, 'docstatus': 1}, pluck="name")

    for je in journal_entries:
        journal_entry = frappe.get_doc('Journal Entry', je)

        journal_entry.cancel()