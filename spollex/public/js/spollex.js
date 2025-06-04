$(document).on("app_ready", function () {
    if (frappe.user_roles.includes("Accountant")) {
        setTimeout(() => {
            frappe.xcall("spollex.utils.show_payments_popup");
        }, 1000);
    }
});