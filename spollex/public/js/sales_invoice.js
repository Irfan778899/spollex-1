//frappe.ui.form.on("Sales Team", {
//    allocated_percentage: function(frm, cdt, cdn){
//        calculate_commission_rate(frm, cdt, cdn);
//    },
//   sales_person: function(frm, cdt, cdn){
//        calculate_commission_rate(frm, cdt, cdn);
//    }
//});

frappe.ui.form.on("Sales Invoice", {
    onload: function(frm) {
        setup_subscription_queries(frm);
        update_old_invoice_link(frm);
    },
    custom_export: function(frm) {
        update_old_invoice_link(frm);
        if (frm.doc.custom_old_invoice) {
            frm.set_value("custom_old_invoice", "");
        }
    },
    custom_subscription_type: function(frm) {
        update_old_invoice_link(frm);
    },
    custom_is_new_subscription: function(frm) {
        update_old_invoice_link(frm);
    },
    before_save: function(frm) {
        update_old_invoice_link(frm);
    },
    refresh: function(frm) {
        update_old_invoice_link(frm);
        if (frm.doc.docstatus === 1 && frm.doc.status != "Paid") {
            frm.add_custom_button(__("Post Sales Credit Note"), function() {
                post_sales_credit_note(frm);
            });
        }
    }
});

frappe.ui.form.on("Subscription Item", {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        let matched_item = (frm.doc.items || []).find(item => item.item_code === row.item_code);
        if (matched_item) {
            frappe.model.set_value(cdt, cdn, "amount", matched_item.amount);
        } else {
            frappe.msgprint(__("Item {0} is not present in the items table.", [row.item_code]));
        }
    }
});

function setup_subscription_queries(frm) {
    frm.set_query("item_code", "custom_subscription_items", function(doc) {
        let items = (doc.items || []).map(item => item.item_code).filter(Boolean);
        return { filters: [["Item", "name", "in", items]] };
    });

    frm.set_query("custom_old_invoice", function(doc) {
        let target_dt = doc.custom_export ? "Sales Order" : "Sales Invoice";
        return {
            filters: {
                customer: doc.customer,
                docstatus: 1,
                custom_renewed: 0
            }
        };
    });
}

function update_old_invoice_link(frm) {
    let target_dt = frm.doc.custom_export ? "Sales Order" : "Sales Invoice";
    let target_label = frm.doc.custom_export ? __("Old Proforma Invoice") : __("Old Invoice");

    // Only set value on editable drafts to avoid dirtying submitted/existing docs
    if (frm.doc.docstatus === 0 && frm.doc.custom_old_doctype !== target_dt) {
        frm.set_value("custom_old_doctype", target_dt);
    }
    frm.set_df_property("custom_old_invoice", "label", target_label);
}

// function calculate_commission_rate(frm, cdt, cdn) {
//     var sales_person_row = locals[cdt][cdn];
//     var total_amount = frm.doc.amount_eligible_for_commission || 0;
//     var allocated_percentage = sales_person_row.allocated_percentage || 0;
//     var allocated_amount = (total_amount * allocated_percentage) * 0.01;
//     var posting_date = frm.doc.posting_date;
//     if (allocated_amount) {
//         frappe.call({
//             method: "spollex.overrides.sales_person.fetch_commission_rate",
//             args : {
//                 sales_person_name: sales_person_row.sales_person,
//                 allocated_amount: allocated_amount,
//                 posting_date: posting_date
//             },
//             callback: function(r) {
//                 if (r.message) {
//                     frappe.model.set_value(cdt, cdn, 'commission_rate', r.message);
//                 } else {
//                     frappe.msgprint(__("Failed to fetch commission rate."));
//                 }
//             }
//         });
//     }
// }

let post_sales_credit_note = async function(frm) {
    const fields = [
        { label: 'Rebate Amount', fieldname: 'rebate_amount', fieldtype: 'Currency' },
        { label: 'Posting Date', fieldname: 'posting_date', fieldtype: 'Date', default: frm.doc.posting_date },
        { label: 'Remark', fieldname: 'remark', fieldtype: 'Small Text' }
    ];

    let d = new frappe.ui.Dialog({
        title: "Post Sales Credit Note",
        fields: fields,
        primary_action_label: "Create Credit Note",
        primary_action: function(values) {
            if (values.rebate_amount <= frm.doc.total) {
                frappe.call({
                    method: 'spollex.utils.create_credit_note',
                    args: {
                        rebate_amount: values.rebate_amount,
                        posting_date: values.posting_date,
                        remark: values.remark,
                        reference_name: frm.doc.name
                    },
                    callback: function(response) {
                        if (response.message) {
                            frappe.msgprint(__("Credit note created successfully"));
                        } else {
                            frappe.msgprint(__("Credit note creation failed"));
                        }
                        d.hide();
                    }
                });
            } else {
                frappe.msgprint(__("The rebate amount cannot exceed the total invoice amount"));
            }
        }
    });
    d.show();
};
