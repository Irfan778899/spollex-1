frappe.ui.form.on("Purchase Invoice", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status != "Paid") {
            frm.add_custom_button(__("Post Purchase Debit Note"), function() {
                post_purchase_debit_note(frm);
            });
        }
    }
});

let post_purchase_debit_note = async function(frm) {

    const fields = [
        {
            label: 'Rebate Amount',
            fieldname: 'rebate_amount',
            fieldtype: 'Currency'
        },
        {
            label: 'Posting Date',
            fieldname: 'posting_date',
            fieldtype: 'Date',
            default: frm.doc.posting_date
        }
    ];
    let tax_rates = [];
    let tax_accounts = [];

    const fetch_tax_rate = async function(tax_row) {
        if (tax_row.rate) {
            tax_rates.push(tax_row.rate);
            tax_accounts.push(tax_row.account_head)
        } else if (tax_row.account_head && tax_row.charge_type == "On Net Total") {
            let response = await frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Account',
                    filters: {name: tax_row.account_head},
                    fieldname: 'tax_rate'
                }
            });
            if (response.message) {
                tax_rates.push(response.message.tax_rate);
                tax_accounts.push(tax_row.account_head);
            } else {
                frappe.throw(__("Failed to fetch tax rate from the tax account"));
            }
        }
    };

    const fetch_all_tax_rates = async function() {
        for (let tax_row of frm.doc.taxes) {
            await fetch_tax_rate(tax_row);
        }
    };

    await fetch_all_tax_rates();

    let d = new frappe.ui.Dialog ({
        title: "Post Purchase Debit Note",
        fields: fields,
        primary_action_label: "Create Debit Note",
        primary_action: function(values) {
            if (values.rebate_amount <= frm.doc.total) {
                frappe.call({
                    method: 'spollex.utils.create_debit_note',
                    args: {
                        party : frm.doc.supplier,
                        rebate_amount : values.rebate_amount,
                        posting_date : values.posting_date,
                        company: frm.doc.company,
                        reference_name: frm.doc.name,
                        tax_accounts: tax_accounts,
                        tax_rates: tax_rates
                    },
                    callback: function(response) {
                        if (response.message) {
                            frappe.msgprint(__("Debit note created successfully"))
                        } else {
                            frappe.msgprint(__("Debit note creation failed"))
                        }
                        d.hide();
                    }
                })
            } else {
                frappe.msgprint(__("The rebate amount cannot exceed the total invoice amount"))
            }
        }
    })
    d.show();
}