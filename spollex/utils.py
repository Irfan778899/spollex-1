# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
import json

@frappe.whitelist()
def create_credit_note(party, rebate_amount, company, reference_name, tax_accounts, tax_rates):

    rebate_amount = float(rebate_amount)

    tax_accounts = json.loads(tax_accounts)
    tax_rates = json.loads(tax_rates)

    journal_entry = frappe.new_doc("Journal Entry")

    journal_entry.voucher_type = "Credit Note"
    journal_entry.posting_date = frappe.utils.nowdate()

    credit_account = frappe.get_cached_value("Company", company, "default_receivable_account")

    debit_account = frappe.get_cached_value("Account", {"account_name": "Rebate Given"}, "name")

    party_type = "Customer"

    total_tax_amount = 0

    for i in range(len(tax_accounts)):
        tax_account = tax_accounts[i]
        tax_rate = float(tax_rates[i])

        tax_amount = rebate_amount * tax_rate / 100
        total_tax_amount += tax_amount


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

    for i in range(len(tax_accounts)):
        tax_account = tax_accounts[i]
        tax_rate = float(tax_rates[i])

        tax_amount = rebate_amount * tax_rate / 100

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

@frappe.whitelist()
def create_debit_note(party, rebate_amount, company, reference_name, tax_accounts, tax_rates):

    rebate_amount = float(rebate_amount)

    tax_accounts = json.loads(tax_accounts)
    tax_rates = json.loads(tax_rates)

    journal_entry = frappe.new_doc("Journal Entry")

    journal_entry.voucher_type = "Debit Note"
    journal_entry.posting_date = frappe.utils.nowdate()

    debit_account = frappe.get_cached_value("Company", company, "default_payable_account")

    credit_account = frappe.get_cached_value("Account", {"account_name": "Rebate Received"}, "name")

    party_type = "Supplier"

    total_tax_amount = 0

    for i in range(len(tax_accounts)):
        tax_account = tax_accounts[i]
        tax_rate = float(tax_rates[i])

        tax_amount = rebate_amount * tax_rate / 100
        total_tax_amount += tax_amount


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

    for i in range(len(tax_accounts)):
        tax_account = tax_accounts[i]
        tax_rate = float(tax_rates[i])

        tax_amount = rebate_amount * tax_rate / 100

        if tax_account and tax_amount > 0:
            journal_entry.append(
                "accounts",
                {
                    "account": tax_account,
                    "party_type": "",
                    "party": "",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": tax_amount,
                },
            )

    journal_entry.save()
    journal_entry.submit()

    return journal_entry