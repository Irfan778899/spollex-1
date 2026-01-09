frappe.ui.form.on("Maintenance Visit", {
    custom_contract(frm) {
        frm.set_query("custom_contract_id", function () {
            return {
                filters: {
                    party_name: frm.doc.customer,
                    status: "Active"
                }
            };
        });
    }
});
