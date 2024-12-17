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

    let d = new frappe.ui.Dialog ({
        title: "Post Purchase Debit Note",
        fields: fields,
        primary_action_label: "Create Debit Note",
        primary_action: function(values) {
            if (values.rebate_amount <= frm.doc.total) {
                frappe.call({
                    method: 'spollex.utils.create_debit_note',
                    args: {
                        rebate_amount : values.rebate_amount,
                        posting_date : values.posting_date,
                        reference_name: frm.doc.name,
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