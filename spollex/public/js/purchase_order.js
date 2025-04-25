frappe.ui.form.on("Purchase Order", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Shipment Tracker"), function() {
                make_shipment_tracker(frm);
            });
        }
    }
});


function make_shipment_tracker() {
    frappe.model.open_mapped_doc({
        method: "spollex.spollex.doctype.shipment_tracker.shipment_tracker.make_shipment_tracker",
        frm: cur_frm,
    });
}