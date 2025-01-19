# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

from spollex.spollex.report.accounts_receivable_with_rebate_given.accounts_receivable_with_rebate_given import ReceivablePayableReport

def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)
