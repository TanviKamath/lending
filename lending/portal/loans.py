# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read-only data for the borrower's loan page.

The endpoint checks ownership of the loan named in the route before reading anything
else. A loan that belongs to someone else and a loan that does not exist raise the
same PermissionError, so the portal never confirms that a record exists -- see
PORTAL_PLAN.md section 8.

Internal risk labels stay out. Delinquency reaches the borrower as a plain overdue
instalment, never as days past due or an NPA classification (section 6.7).
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from lending.portal.core import (
	STATUS_LABELS,
	assert_owns,
	get_loans,
	get_portal_customers,
	is_live,
	long_date,
	money,
	shell_payload,
)

# Loan fields the borrower may see. The risk fields are simply never selected.
DETAIL_FIELDS = (
	"name",
	"applicant",
	"loan_product",
	"status",
	"loan_amount",
	"disbursed_amount",
	"rate_of_interest",
	"repayment_periods",
	"repayment_frequency",
	"repayment_start_date",
	"monthly_repayment_amount",
	"total_payment",
	"total_amount_paid",
	"total_principal_paid",
	"total_interest_payable",
	"written_off_amount",
)


@frappe.whitelist()
def get_loan_detail() -> dict:
	"""One loan's page. With no loan named, the borrower's main loan -- see default_loan."""
	name = frappe.form_dict.get("name") or default_loan()
	if not name:
		return no_loan_payload()

	assert_owns("Loan", name)
	loan = frappe.db.get_value("Loan", name, DETAIL_FIELDS, as_dict=True)

	payload = shell_payload(loan.loan_product, _("Download statement"), [loan])
	payload["crumb"] = loan.loan_product
	payload["head_note"] = "{0} · {1}".format(loan.name, STATUS_LABELS.get(loan.status, loan.status))

	payload.update(
		{
			"product": loan.loan_product,
			"terms": loan_terms(loan),
			"summary_note": _("Key information about your loan."),
			"charges": charge_rows(name),
			**payoff_figures(name),
		}
	)

	return payload


def default_loan() -> str | None:
	"""The loan the sidebar opens: the newest live one, else the newest of any.

	The sidebar goes straight to a loan rather than to a list of them. A borrower with
	more than one loan still reaches the others from the overview and from search.
	"""
	customers = get_portal_customers()
	loans = get_loans(customers) if customers else []
	if not loans:
		return None

	newest = sorted(loans, key=lambda loan: loan.posting_date, reverse=True)
	live = [loan for loan in newest if is_live(loan)]

	return (live or newest)[0].name


def no_loan_payload() -> dict:
	"""The page for a borrower with no loan yet: the frame, and every card empty."""
	payload = shell_payload(_("Loan account"), _("Apply for a loan"), [])
	payload.update(
		{
			"product": "",
			"terms": None,
			"summary_note": _("No loan accounts yet"),
			"charges": [],
			"payoff_total": money(0),
			"payoff_note": _("Nothing outstanding"),
		}
	)

	return payload


def loan_terms(loan: dict) -> dict:
	"""The terms by name, because the card places each one rather than repeating over them."""
	written_off = flt(loan.written_off_amount)

	return {
		"sanctioned": money(loan.loan_amount),
		"disbursed": money(loan.disbursed_amount),
		"rate": "{0}%".format(flt(loan.rate_of_interest, 2)),
		"tenure": tenure(loan),
		"instalment": money(loan.monthly_repayment_amount),
		"frequency": _(loan.repayment_frequency or "Monthly"),
		"total": money(loan.total_payment),
		"paid": money(loan.total_amount_paid),
		"first_due": long_date(loan.repayment_start_date),
		"written_off": _("{0} written off").format(money(written_off)) if written_off else "",
	}


def tenure(loan: dict) -> str:
	"""Months when the loan is repaid monthly; otherwise the count of instalments."""
	periods = loan.repayment_periods or 0
	if (loan.repayment_frequency or "Monthly") == "Monthly":
		return _("{0} months").format(periods)

	return _("{0} instalments").format(periods)


def charge_rows(loan: str) -> list[dict]:
	rows = frappe.get_all(
		"Loan Disbursement Charge",
		filters={"parent": loan, "parenttype": "Loan"},
		fields=["charge", "amount", "treatment_of_charge"],
		ignore_permissions=True,
	)

	return [
		{
			"label": row.charge,
			"value": money(row.amount),
			"detail": row.treatment_of_charge or "",
		}
		for row in rows
	]


def payoff_figures(loan: str) -> dict:
	"""What it costs to close the loan today, and the line under the figure.

	PORTAL_PLAN.md section 6.11: show the figure, never take the money. The button
	under this raises a request for staff.

	The figure is always a sum of money, ₹ 0.00 included, because the card prints it
	at the same size either way; the note is what tells a settled loan from a live one.
	"""
	from lending.loan_management.doctype.loan_repayment.loan_repayment import calculate_amounts

	try:
		payable = flt(calculate_amounts(loan, nowdate(), payment_type="Loan Closure").get("payable_amount"))
	except Exception:
		# A closed or written-off loan has nothing left to price.
		frappe.clear_last_message()
		payable = 0

	return {
		"payoff_total": money(max(payable, 0)),
		"payoff_note": (
			_("As on {0}").format(long_date(nowdate())) if payable > 0 else _("Nothing outstanding")
		),
	}
