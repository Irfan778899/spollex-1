frappe.ui.form.on("Sales Order", {
    onload: function(frm) {
        update_old_invoice_link(frm);
        frm.set_query("item_code", "custom_subscription_items", function(doc, cdt, cdn) {
            let items = (doc.items || []).map(item => item.item_code).filter(Boolean);
            return {
                filters: [
                    ["Item", "name", "in", items]
                ]
            };
        });
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
        let subscription_items = frm.doc.custom_subscription_items || [];
        let doc_items = frm.doc.items || [];

        let item_amount_map = {};
        doc_items.forEach(item => {
            if (item.item_code) {
                item_amount_map[item.item_code] = (item_amount_map[item.item_code] || 0) + (item.amount || 0);
            }
        });

        subscription_items.forEach(row => {
            if (row.item_code && item_amount_map[row.item_code] !== undefined) {
                frappe.model.set_value(row.doctype, row.name, "amount", item_amount_map[row.item_code]);
            }
        });
    }
});

function update_old_invoice_link(frm) {
    let target_dt = frm.doc.custom_export ? "Sales Order" : "Sales Invoice";
    let target_label = frm.doc.custom_export ? __("Old Proforma Invoice") : __("Old Invoice");
    if (frm.doc.custom_old_doctype !== target_dt) {
        frm.set_value("custom_old_doctype", target_dt);
    }
    frm.set_df_property("custom_old_invoice", "label", target_label);
}

frappe.ui.form.on("Subscription Item", {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code) {
            setTimeout(() => {
                let matched_item = (frm.doc.items || []).find(item => item.item_code === row.item_code);
                if (matched_item) {
                    frappe.model.set_value(cdt, cdn, "amount", matched_item.amount);
                } else {
                    frappe.msgprint(__("Item 0 is not present in the items table.", [row.item_code]));
                }
            }, 100);
        }
    }
});
