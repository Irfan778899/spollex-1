# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of
from collections import defaultdict

from erpnext.accounts.report.financial_statements import (
	compute_growth_view_data,
	compute_margin_view_data,
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)


def execute(filters=None):
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	filters.company_abbr = frappe.get_cached_value("Company", filters.company, "abbr")

	direct_account_root = f"Direct Expenses - {filters.company_abbr}"
	indirect_account_root = f"Indirect Expenses - {filters.company_abbr}"

	direct_expense_accounts = get_descendants_of("Account", direct_account_root)
	indirect_expense_accounts = get_descendants_of("Account", indirect_account_root)

	direct_expense = []
	indirect_expense = []

	for row in expense:
		account = row.get("account")
		if not account:
			continue
		if account in direct_expense_accounts or account == direct_account_root:
			direct_expense.append(row)
		elif account in indirect_expense_accounts or account == indirect_account_root:
			indirect_expense.append(row)

	reset_indent_tree(direct_expense, direct_account_root)
	reset_indent_tree(indirect_expense, indirect_account_root)

	gross_profit_loss = get_gross_profit_loss(
		income, direct_expense, period_list, filters.company, filters.presentation_currency
	)

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)

	data = []
	data.extend(income or [])
	data.extend(direct_expense or [])
	if gross_profit_loss:
		data.append(gross_profit_loss)
	data.append({})
	data.extend(indirect_expense or [])
	for row in expense or []:
		if row.get("account") == "'Total Expense (Debit)'":
			data.append(row)
			break
	data.append({})
	if net_profit_loss:
		data.append(net_profit_loss)

	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	chart = get_chart_data(filters, columns, income, direct_expense, gross_profit_loss, indirect_expense, net_profit_loss, currency)

	report_summary, primitive_summary = get_report_summary(
		period_list, filters.periodicity, income, direct_expense, gross_profit_loss, indirect_expense, net_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	if filters.get("selected_view") == "Margin":
		compute_margin_view_data(data, period_list, filters.accumulated_values)

	return columns, data, None, chart, report_summary, primitive_summary


def get_report_summary(
	period_list, periodicity, income, direct_expense, gross_profit_loss,
	indirect_expense, net_profit_loss, currency, filters, consolidated=False
):
	net_income, net_direct_expense, gross_profit, net_indirect_expense, net_profit = 0.0, 0.0, 0.0, 0.0, 0.0

	# Apply consolidated filtering
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	if filters.accumulated_values:
		key = period_list[-1].key
		if income:
			net_income = income[-2].get(key, 0.0)
		if direct_expense:
			net_direct_expense = direct_expense[0].get(key, 0.0)
		if gross_profit_loss:
			gross_profit = gross_profit_loss.get(key, 0.0)
		if indirect_expense:
			net_indirect_expense = indirect_expense[0].get(key, 0.0)
		if net_profit_loss:
			net_profit = net_profit_loss.get(key, 0.0)
	else:
		for period in period_list:
			key = period if consolidated else period.key
			if income:
				net_income += income[-2].get(key, 0.0)
			if direct_expense:
				net_direct_expense += direct_expense[0].get(key, 0.0)
			if gross_profit_loss:
				gross_profit += gross_profit_loss.get(key, 0.0)
			if indirect_expense:
				net_indirect_expense += indirect_expense[0].get(key, 0.0)
			if net_profit_loss:
				net_profit += net_profit_loss.get(key, 0.0)

	if len(period_list) == 1 and periodicity == "Yearly":
		income_label = _("Total Income This Year")
		direct_label = _("Direct Expenses This Year")
		gross_profit_label = _("Gross Profit This Year")
		indirect_label = _("Indirect Expenses This Year")
		net_profit_label = _("Net Profit This Year")
	else:
		income_label = _("Total Income")
		direct_label = _("Direct Expenses")
		gross_profit_label = _("Gross Profit")
		indirect_label = _("Indirect Expenses")
		net_profit_label = _("Net Profit")

	return [
		{"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": net_direct_expense, "label": direct_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": gross_profit,
			"indicator": "Green" if gross_profit > 0 else "Red",
			"label": gross_profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
		{"type": "separator", "value": "-"},
		{"value": net_indirect_expense, "label": indirect_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": net_profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	], net_profit


def get_gross_profit_loss(income, direct_expense, period_list, company, currency=None, consolidated=False):
	total = 0
	gross_profit_loss = {
		"account_name": "'" + _("Gross Profit") + "'",
		"account": "'" + _("Gross Profit") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		direct_expense = flt(direct_expense[0][key], 3) if direct_expense else 0
		
		gross_profit_loss[key] = total_income - direct_expense

		if gross_profit_loss[key]:
			has_value = True

		total += flt(gross_profit_loss[key])
		gross_profit_loss["total"] = total

	if has_value:
		return gross_profit_loss


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
	total = 0
	net_profit_loss = {
		"account_name": "'" + _("Net Profit") + "'",
		"account": "'" + _("Net Profit") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency")
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss


def get_chart_data(filters, columns, income, direct_expense, gross_profit_loss, indirect_expense, net_profit_loss, currency):
	labels = [d.get("label") for d in columns[2:]]

	income_data, direct_data, gross_data, indirect_data, net_data = [], [], [], [], []

	for col in columns[2:]:
		fieldname = col.get("fieldname")
		if income:
			income_data.append(income[-2].get(fieldname, 0.0))
		if direct_expense:
			direct_data.append(direct_expense[0].get(fieldname, 0.0))
		if gross_profit_loss:
			gross_data.append(gross_profit_loss.get(fieldname, 0.0))
		if indirect_expense:
			indirect_data.append(indirect_expense[0].get(fieldname, 0.0))
		if net_profit_loss:
			net_data.append(net_profit_loss.get(fieldname, 0.0))

	datasets = []
	if any(income_data):
		datasets.append({"name": _("Income"), "values": income_data})
	if any(direct_data):
		datasets.append({"name": _("Direct Expenses"), "values": direct_data})
	if any(gross_data):
		datasets.append({"name": _("Gross Profit"), "values": gross_data})
	if any(indirect_data):
		datasets.append({"name": _("Indirect Expenses"), "values": indirect_data})
	if any(net_data):
		datasets.append({"name": _("Net Profit"), "values": net_data})

	chart = {
		"data": {
			"labels": labels,
			"datasets": datasets
		},
		"type": "line" if filters.accumulated_values else "bar",
		"fieldtype": "Currency",
		"options": "currency",
		"currency": currency
	}

	return chart


def reset_indent_tree(expense_rows, root_account_name):
	from collections import defaultdict

	# Build account lookup and parent-child map
	account_map = {}
	child_map = defaultdict(list)

	for row in expense_rows:
		account = row.get("account")
		parent = row.get("parent_account")
		if account:
			account_map[account] = row
		if parent:
			child_map[parent].append(account)

	# Recursive function to set indent
	def set_indent(account, indent_level):
		row = account_map.get(account)
		if row:
			row["indent"] = indent_level
			for child in child_map.get(account, []):
				set_indent(child, indent_level + 1)

	set_indent(root_account_name, 0)


