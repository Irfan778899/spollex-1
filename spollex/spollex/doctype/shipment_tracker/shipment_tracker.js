// Copyright (c) 2025, 4C Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shipment Tracker", {
	refresh(frm) {
        frm.set_query('forwarder', function() {
            return {
              filters: {
                is_transporter: 1
              }
            };
        });
	},
});
