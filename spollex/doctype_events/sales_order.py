# Copyright (c) 2026, 4C Solutions and contributors
# For license information, please see license.txt

from spollex.doctype_events.subscription import (
	validate_subscription_details,
	update_renewal_invoice_status,
)


def update_renewal_invoice_status_on_submit_cancel(doc, method=None):
	update_renewal_invoice_status(doc, method=method, is_export=True)
