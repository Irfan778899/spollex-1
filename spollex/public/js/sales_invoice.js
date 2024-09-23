frappe.ui.form.on("Sales Team", {
    allocated_percentage: function(frm, cdt, cdn){
        calculate_commission_rate(frm, cdt, cdn);
    },
    sales_person: function(frm, cdt, cdn){
        calculate_commission_rate(frm, cdt, cdn);
    }
});

frappe.ui.form.on("Sales Invoice", {
    before_save: function(frm){
        frm.doc.sales_team.forEach((record) => {
            calculate_commission_rate(frm, record.doctype, record.name);
        });
    },
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 & frm.doc.status != "Paid") {
            frm.add_custom_button(__("Post Sales Credit Note"), function() {
                post_sales_credit_note(frm);
            });
        }
    }
});

function calculate_commission_rate(frm, cdt, cdn) {
    var sales_person_row = locals[cdt][cdn];
    var total_amount = frm.doc.amount_eligible_for_commission || 0;
    var allocated_percentage = sales_person_row.allocated_percentage || 0;
    var allocated_amount = (total_amount * allocated_percentage) * 0.01;
    var posting_date = frm.doc.posting_date;

    if (allocated_amount) {
        frappe.call({
            method: "spollex.overrides.sales_person.fetch_commission_rate",
            args : {
                sales_person_name: sales_person_row.sales_person,
                allocated_amount: allocated_amount,
                posting_date: posting_date
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, 'commission_rate', r.message);
                } else {
                    frappe.msgprint(__("Failed to fetch commission rate."));
                }
            }
        });
    }
}

let post_sales_credit_note = function(frm) {

    const fields = [
        {
            label: 'Rebate Amount',
            fieldname: 'rebate_amount',
            fieldtype: 'Currency'
        }
    ];
    let tax_rate = 0;

    frm.doc.taxes.forEach((tax_row)=> {
        if (tax_row.rate) {
            tax_rate = tax_row.rate;
            tax_account = tax_row.account_head
        } else if (tax_row.account_head) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Account',
                    filters: { name: tax_row.account_head },
                    fieldname: 'tax_rate'
                },
                callback: function(response) {
                    if (response.message) {
                        tax_rate = response.message.tax_rate;
                        tax_account = tax_row.account_head;
                    }
                }
            });
        }
    });

    let d = new frappe.ui.Dialog ({
        title: "Post Sales Credit Note",
        fields: fields,
        primary_action_label: "Create Credit Note",
        primary_action: function(values) {
            frappe.call({
                method: 'spollex.utils.create_credit_note',
                args: {
                    party : frm.doc.customer,
                    rebate_amount : values.rebate_amount,
                    company: frm.doc.company,
                    reference_name: frm.doc.name,
                    tax_account: tax_account,
                    tax_rate: tax_rate
                },
                callback: function(response) {
                    if (response.message) {
                        frappe.msgprint(__("Credit note created successfully"))
                    } else {
                        frappe.msgprint(__("Credit note creation failed"))
                    }
                    d.hide();
                }
            })
        }
    })
    d.show();
}