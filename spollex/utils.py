# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
import json

@frappe.whitelist()
def create_credit_note(rebate_amount, posting_date, reference_name):
    sales_invoice = frappe.get_doc("Sales Invoice", reference_name)
    company = sales_invoice.get("company")

    rebate_amount = float(rebate_amount)

    currency = sales_invoice.get("currency")
    conversion_rate = sales_invoice.get("conversion_rate")

    if currency != frappe.get_cached_value("Company", company, "default_currency") and conversion_rate:
        rebate_amount = rebate_amount * conversion_rate

    journal_entry = frappe.new_doc("Journal Entry")

    journal_entry.voucher_type = "Credit Note"
    journal_entry.posting_date = posting_date

    credit_account = frappe.get_cached_value("Company", company, "default_receivable_account")

    debit_account = frappe.get_cached_value("Account", {"account_name": "Rebate Given"}, "name")

    party_type = "Customer"

    party = sales_invoice.get("customer")

    total_tax_amount = 0
    vat_entries = []

    tax_rows = sales_invoice.get("taxes")

    for row in tax_rows:
        tax_rate = None

        if row.rate:
            tax_rate = float(row.rate)
        elif row.account_head and row.charge_type == "On Net Total":
            tax_rate = frappe.get_value("Account", row.account_head, "tax_rate")
            if tax_rate is None:
                frappe.throw(f"Failed to fetch tax rate for account: {row.account_head}")

        if tax_rate:
            tax_amount = rebate_amount * tax_rate / 100
            total_tax_amount += tax_amount

            if row.account_head and tax_amount > 0:
                vat_entries.append(
                    {
                        "account": row.account_head,
                        "party_type": "",
                        "party": "",
                        "debit_in_account_currency": tax_amount,
                        "credit_in_account_currency": 0,
                    }
                )

    credit_amount = rebate_amount + total_tax_amount

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

    for vat_entry in vat_entries:
        journal_entry.append("accounts", vat_entry)

    journal_entry.save()
    journal_entry.submit()

    return journal_entry

@frappe.whitelist()
def create_debit_note(rebate_amount, posting_date, reference_name):
    purchase_invoice = frappe.get_doc("Purchase Invoice", reference_name)
    company = purchase_invoice.get("company")

    rebate_amount = float(rebate_amount)
    currency = purchase_invoice.get("currency")
    conversion_rate = purchase_invoice.get("conversion_rate")
    reverse_charge = purchase_invoice.get("reverse_charge")

    if currency != frappe.get_cached_value("Company", company, "default_currency") and conversion_rate:
        rebate_amount = rebate_amount * conversion_rate

    journal_entry = frappe.new_doc("Journal Entry")

    journal_entry.voucher_type = "Debit Note"
    journal_entry.posting_date = posting_date

    debit_account = frappe.get_cached_value("Company", company, "default_payable_account")

    credit_account = frappe.get_cached_value("Account", {"account_name": "Rebate Received"}, "name")

    party_type = "Supplier"
    party = purchase_invoice.get("supplier")

    total_tax_amount = 0
    vat_entries = []

    tax_rows = purchase_invoice.get("taxes")

    if reverse_charge == "N":
        for row in tax_rows:
            tax_rate = None
            if row.rate:
                tax_rate = float(row.rate)
            elif row.account_head and row.charge_type == "On Net Total":
                tax_rate = frappe.get_value("Account", row.account_head, "tax_rate")
                if tax_rate is None:
                    frappe.throw(f"Failed to fetch tax rate for account: {row.account_head}")

            if tax_rate:
                tax_amount = rebate_amount * tax_rate / 100
                total_tax_amount += tax_amount

                if row.account_head and tax_amount > 0:
                    vat_entries.append(
                        {
                            "account": row.account_head,
                            "party_type": "",
                            "party": "",
                            "debit_in_account_currency": 0,
                            "credit_in_account_currency": tax_amount,
                        }
                    )


    debit_amount = rebate_amount + total_tax_amount

    journal_entry.append(
        "accounts",
        {
            "account": debit_account,
            "party_type": party_type,
            "party": party,
            "debit_in_account_currency": debit_amount,
            "credit_in_account_currency": 0,
            "reference_type": "Purchase Invoice",
            "reference_name": reference_name
        },
    )

    journal_entry.append(
        "accounts",
        {
            "account": credit_account,
            "party_type": "",
            "party": "",
            "debit_in_account_currency": 0,
            "credit_in_account_currency": rebate_amount,
        },
    )

    for vat_entry in vat_entries:
        journal_entry.append("accounts", vat_entry)

    journal_entry.save()
    journal_entry.submit()

    return journal_entry