//frappe.ui.form.on("Sales Team", {
//    allocated_percentage: function(frm, cdt, cdn){
//        calculate_commission_rate(frm, cdt, cdn);
//    },
//   sales_person: function(frm, cdt, cdn){
//        calculate_commission_rate(frm, cdt, cdn);
//    }
//});

frappe.ui.form.on("Sales Invoice", {
    // frm.doc.sales_team.forEach((record) => {
    //         before_save: function(frm){
    //         calculate_commission_rate(frm, record.doctype, record.name);
    //     });
    // },
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status != "Paid") {
            frm.add_custom_button(__("Post Sales Credit Note"), function() {
                post_sales_credit_note(frm);
            });
        }
    }
});

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
        title: "Post Sales Credit Note",
        fields: fields,
        primary_action_label: "Create Credit Note",
        primary_action: function(values) {
            if (values.rebate_amount <= frm.doc.total) {
                frappe.call({
                    method: 'spollex.utils.create_credit_note',
                    args: {
                        rebate_amount : values.rebate_amount,
                        posting_date : values.posting_date,
                        reference_name: frm.doc.name
                    },
                    callback: function(response) {
                        if (response.message) {
                            frappe.msgprint(__("Credit note created successfully"))
                        } else {
                            frappe.msgprint(__("Credit note creation failed"))
                        }
                        d.hide();
                    }
                });
            } else {
                frappe.msgprint(__("The rebate amount cannot exceed the total invoice amount"))
            }
        }
    })
    d.show();
}