# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, add_days, formatdate
from frappe import _

@frappe.whitelist()
def create_credit_note(rebate_amount, posting_date, reference_name, remark=None):
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
    if remark:
        journal_entry.user_remark = remark

    credit_account = frappe.get_cached_value("Company", company, "default_receivable_account")

    debit_account = frappe.get_cached_value("Account", {"account_name": "Credit Notes (Rebate Given)"}, "name")

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
def create_debit_note(rebate_amount, posting_date, reference_name, remark=None):
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
    if remark:
        journal_entry.user_remark = remark

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
        formatted_expiry_date = formatdate(expiry_date_30_days_from_now, "dd-mm-yyyy")
        sabb = frappe.db.get_value('Serial and Batch Entry', filters={'serial_no': nos.name, 'is_outward': 1}, fieldname='parent')

        if sabb:
            sabb_doc = frappe.get_doc('Serial and Batch Bundle', sabb)

            if sabb_doc.item_group in ['SANGFOR', 'SANGFOR Licenses']:

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
                        "expiry_date": formatted_expiry_date,
                        "serial_no": nos.name,
                        "item_code": frappe.db.get_value("Serial No", nos.name, "item_code"),
                        "item_description": frappe.db.get_value("Serial No", nos.name, "description"),
                        "end_customer": end_customer,
                        "end_customer_email": end_customer_email,
                        "company": si_doc.company,
                        "company_email": company_email
                    }

                    email_targets = [
                        ("Warranty Expiry Notification to Partner", customer_email),
                        ("Warranty Expiry Notification to End User", end_customer_email),
                        ("Warranty Expiry Notification to Distributor", company_email)
                    ]

                    for template_name, recipient_email in email_targets:
                        if recipient_email:
                            send_email_notification(template_name, [recipient_email], doc_args, "Serial No", nos.name)

    frappe.db.commit()
    frappe.msgprint("Warranty expiry notifications sent successfully.")

@frappe.whitelist()
def send_subscription_expiry_notification():
    expiry_date_30_days_from_now = add_days(nowdate(), 30)

    sales_invoices = frappe.get_all(
        'Sales Invoice',
        filters={'to_date': expiry_date_30_days_from_now, 'docstatus': 1},
        fields=['name', 'contact_email', 'customer', 'customer_address', 'custom_end_customer', 'custom_end_customer_email', 'company_address', 'to_date', 'company']
    )

    for invoice in sales_invoices:
        formatted_expiry_date = formatdate(invoice.to_date, "dd-mm-yyyy")
        customer_email = invoice.contact_email
        if not customer_email:
            customer_email = frappe.db.get_value('Address', {"name": invoice.customer_address}, 'email_id')
        
        end_customer = invoice.custom_end_customer
        end_customer_email = invoice.custom_end_customer_email

        company_address_id = invoice.company_address
        company_email = frappe.db.get_value('Address', {"name": company_address_id}, 'email_id')

        items = frappe.get_all("Sales Invoice Item", filters={"parent": invoice.name}, fields=['item_code', 'item_group'])

        item_codes_str = ""
        for item in items:
            if item.item_group in ['SANGFOR', 'SANGFOR Licences']:
                item_codes_str += item.item_code +  "/"

        if item_codes_str:
            item_codes_str = item_codes_str.rstrip(" / ")

            doc_args = {
                "sales_invoice": invoice.name,
                "customer_name": invoice.customer,
                "expiry_date": formatted_expiry_date,
                "item_code": item_codes_str,
                "end_customer": end_customer,
                "end_customer_email": end_customer_email,
                "company": invoice.company,
                "company_email": company_email
            }

            email_targets = [
                ("Warranty Expiry Notification to Partner", customer_email),
                ("Warranty Expiry Notification to End User", end_customer_email),
                ("Warranty Expiry Notification to Distributor", company_email)
            ]

            for template_name, recipient_email in email_targets:
                if recipient_email:
                    send_email_notification(template_name, [recipient_email], doc_args, "Sales Invoice", invoice.name)

    frappe.db.commit()
    frappe.msgprint("Subscription expiry notifications sent successfully.")

def send_email_notification(template_name, recipients, doc_args, doctype, docname):
    email_template = frappe.get_doc("Email Template", template_name)
    subject = frappe.render_template(email_template.subject, doc_args)
    message = frappe.render_template(email_template.response_, doc_args)

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        reference_doctype=doctype,
        reference_name=docname,
    )

def update_shipment_tracker_status():
    shipment_trackers = frappe.get_all("Shipment Tracker", filters={"status": ["!=", "Received"]}, fields=["name"])

    for tracker in shipment_trackers:
        shipment_tracker = frappe.get_doc("Shipment Tracker", tracker.name)
        shipment_tracker.set_status()
        shipment_tracker.save()
    frappe.db.commit()

@frappe.whitelist()
def show_payments_popup():
    today = nowdate()
    due_date = add_days(today, 7)

    message = []

    purchase_invoices = frappe.get_all("Purchase Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": ("between", [today, due_date])
        },
        fields=["name", "supplier", "due_date", "outstanding_amount"]
    )

    if purchase_invoices:
        message.append(["<b>Payments Due (Purchase Invoices)</b>", "", "", ""])
        message.append(["Invoice", "Supplier", "Due Date", "Outstanding Amount"])
        for inv in purchase_invoices:
            message.append([
                inv.name,
                inv.supplier,
                formatdate(inv.due_date, 'dd-mm-yyyy'),
                format(inv.outstanding_amount, '.2f')
            ])

    sales_invoices = frappe.get_all("Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": ("between", [today, due_date])
        },
        fields=["name", "customer", "due_date", "outstanding_amount"]
    )

    if sales_invoices:
        message.append(["<b>Receipts Due (Sales Invoices)</b>", "", "", ""])
        message.append(["Invoice", "Customer", "Due Date", "Outstanding Amount"])
        for inv in sales_invoices:
            message.append([
                inv.name,
                inv.customer,
                formatdate(inv.due_date, 'dd-mm-yyyy'),
                format(inv.outstanding_amount, '.2f')
            ])

    if message:
        frappe.msgprint(
            msg=message,
            title="Payments/Receipts Due in Next 7 Days",
            indicator="orange",
            primary_action=None,
            as_table=1
        )
    else:
        frappe.msgprint("No Payments/Receipts due in the next 7 days.", title="No Pending Invoices", indicator="green")

@frappe.whitelist()
def add_additional_visits_to_contract(contract_name, visit_type, additional_visits):
    contract = frappe.get_doc("Contract", contract_name)
    visit_found = False
    for visit in contract.custom_contract_visit_details:
        if visit.visit_type == visit_type:
            visit_found = True
            frappe.db.set_value(
                "Contract Visit Detail",
                visit.name,
                {
                    "total_visits": visit.total_visits + int(additional_visits),
                    "balance_visits": visit.balance_visits + int(additional_visits)
                }
            )
            contract.reload()
            break
    
    if not visit_found:
        frappe.throw(_("Visit Type {0} not found in Contract {1}").format(visit_type, contract_name))

    return