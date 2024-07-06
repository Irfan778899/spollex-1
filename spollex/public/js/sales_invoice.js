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