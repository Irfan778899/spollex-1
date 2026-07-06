frappe.ui.form.on("Sales Order", {
    onload: function(frm) {
        setup_subscription_queries(frm);
        update_old_invoice_link(frm);
    },
    refresh: function(frm) {
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
