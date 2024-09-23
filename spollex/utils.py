# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

import frappe

@frappe.whitelist()
def create_credit_note(party, rebate_amount, company, reference_name, tax_account, tax_rate):

    rebate_amount = float(rebate_amount)
    tax_rate = float(tax_rate)

    journal_entry = frappe.new_doc("Journal Entry")

    journal_entry.voucher_type = "Credit Note"
    journal_entry.posting_date = frappe.utils.nowdate()

    credit_account = frappe.get_cached_value("Company", company, "default_receivable_account")

    debit_account = frappe.get_cached_value("Company", company, "default_income_account")

    party_type = "Customer"

    tax_amount = rebate_amount * tax_rate/100

    credit_amount = rebate_amount + tax_amount

    journal_entry.append(
        "accounts",
        {
            "account": credit_account,
            "party_type": party_type,
            "party": party,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": credit_amount,
            "reference_type": "Sales Invoice",
            "reference_name": reference_name
        },
    )

    journal_entry.append(
        "accounts",
        {
            "account": debit_account,
            "party_type": "",
            "party": "",
            "debit_in_account_currency": rebate_amount,
            "credit_in_account_currency": 0,
        },
    )

    if tax_account and tax_amount > 0:
        journal_entry.append(
            "accounts",
            {
                "account": tax_account,
                "party_type": "",
                "party": "",
                "debit_in_account_currency": tax_amount,
                "credit_in_account_currency": 0,
            },
        )

    journal_entry.save()
    journal_entry.submit()

    return journal_entry