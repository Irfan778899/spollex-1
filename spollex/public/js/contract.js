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
