frappe.ui.form.on("Contract", {
    refresh(frm) {
        // Add custom button to increase visits
        if (frm.doc.status === "Active") {
            frm.add_custom_button("Increase Visits", () => {
                frappe.prompt([
                    {
                        label: "Visit Type",
                        fieldname: "visit_type",
                        fieldtype: "Link",
                        options: "Visit Type",
                        reqd: 1
                    },
                    {
                        label: "Additional Visits",
                        fieldname: "additional_visits",
                        fieldtype: "Int",
                        reqd: 1
                    }
                ],
                (values) => {
                    frappe.call({
                        method: "spollex.utils.add_additional_visits_to_contract",
                        args: {
                            contract_name: frm.doc.name,
                            visit_type: values.visit_type,
                            additional_visits: values.additional_visits
                        },
                        callback: function(response) {
                            frm.reload_doc();
                        }
                    });
                });
            });
        }
    }
});

frappe.ui.form.on("Contract Visit Detail", {
    total_visits(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // Initialize balance ONLY once
        if (row.total_visits) {
            row.balance_visits = row.total_visits;

            frm.refresh_field("custom_contract_visit_details");
        }
    }
});
