# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt


from spollex.spollex.report.receivable_summary_with_rebate_given.receivable_summary_with_rebate_given import (
	AccountsReceivableSummary,
)


def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return AccountsReceivableSummary(filters).run(args)