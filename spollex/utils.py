# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, add_days
from frappe import _
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

@frappe.whitelist()
def send_warranty_expiry_notification():
    expiry_date_30_days_from_now = add_days(nowdate(), 30)

    # Query Serial Numbers with expiry date in the next 30 days
    serial_nos = frappe.db.get_all('Serial No', filters={'warranty_expiry_date': expiry_date_30_days_from_now, 'status': 'Delivered'}, fields=['name'])

    for nos in serial_nos:
        sabb = frappe.db.get_value('Serial and Batch Entry', filters={'serial_no': nos.name, 'is_outward': 1}, fieldname='parent')

        if sabb:
            sabb_doc = frappe.get_doc('Serial and Batch Bundle', sabb)

            voucher_type = sabb_doc.voucher_type
            voucher_no = sabb_doc.voucher_no

            if voucher_type == 'Delivery Note':
                # Fetch the corresponding Sales Invoice from Delivery Note
                sales_invoice = frappe.db.get_value('Delivery Note Item', {'parent': voucher_no}, 'against_sales_invoice')
            elif voucher_type == 'Sales Invoice':
                sales_invoice = voucher_no
            else:
                sales_invoice = None

            if sales_invoice:
                si_doc = frappe.get_doc('Sales Invoice', sales_invoice)
                customer_email = si_doc.contact_email
                if not customer_email:
                    customer_address_id = si_doc.customer_address
                    customer_email = frappe.db.get_value('Address', {"name": customer_address_id}, 'email_id')

                end_customer = si_doc.custom_end_customer
                end_customer_email = si_doc.custom_end_customer_email

                company_address_id = si_doc.company_address
                company_email = frappe.db.get_value('Address', {"name": company_address_id}, 'email_id')

                doc_args = {
                    "sales_invoice": sales_invoice,
                    "customer_name": si_doc.customer_name,
                    "expiry_date": expiry_date_30_days_from_now,
                    "serial_no": nos.name,
                    "item_code": frappe.db.get_value("Serial No", nos.name, "item_code"),
                    "item_description": frappe.db.get_value("Serial No", nos.name, "description"),
                    "end_customer": end_customer,
                    "end_customer_email": end_customer_email
                }

                send_email_notification("Warranty Expiry Notification", [customer_email, end_customer_email, company_email], doc_args, "Serial No", nos.name)

    frappe.msgprint("Warranty expiry notifications sent successfully.")

@frappe.whitelist()
def send_subscription_expiry_notification():
    expiry_date_30_days_from_now = add_days(nowdate(), 30)

    sales_invoices = frappe.get_all(
        'Sales Invoice',
        filters={'to_date': expiry_date_30_days_from_now},
        fields=['name', 'contact_email', 'customer', 'customer_address', 'custom_end_customer', 'custom_end_customer_email', 'company_address', 'to_date', 'company']
    )

    for invoice in sales_invoices:

        customer_email = invoice.contact_email
        if not customer_email:
            customer_email = frappe.db.get_value('Address', {"name": invoice.customer_address}, 'email_id')
        
        end_customer = invoice.custom_end_customer
        end_customer_email = invoice.custom_end_customers_email

        company_address_id = invoice.company_address
        company_email = frappe.db.get_value('Address', {"name": company_address_id}, 'email_id')

        doc_args = {
            "sales_invoice": invoice.name,
            "customer_name": invoice.customer_name,
            "expiry_date": invoice.to_date,
            "end_customer": end_customer,
            "end_customer_email": end_customer_email
        }

        send_email_notification("Subscription Expiry Notification", [customer_email, end_customer_email, company_email], doc_args, "Sales Invoice", invoice.name)

    frappe.msgprint("Subscription expiry notifications sent successfully.")

def send_email_notification(template_name, recipients, doc_args, doctype, docname):
    recipients = [email for email in recipients if email]
    if not recipients:
        return

    email_template = frappe.get_doc("Email Template", template_name)
    subject = frappe.render_template(email_template.subject, doc_args)
    content = frappe.render_template(email_template.response_, doc_args)

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=content,
        reference_doctype=doctype,
        reference_name=docname,
    )

    frappe.msgprint(_("Email Sent to Recipients: {0}").format(", ".join(recipients)))