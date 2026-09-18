# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read-only data for the borrower's loan list and loan detail pages.

Both endpoints resolve the borrower's own Customer records first, and the detail
endpoint checks ownership of the loan named in the route before reading anything
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
	build_summary,
	get_loans,
	get_portal_customers,
	get_upcoming_repayments,
	labels,
	long_date,
	money,
	present_loan,
	shell_payload,
	short_date,
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
def get_loans_page() -> dict:
	"""Every loan the borrower holds, one row per loan, each linking to its detail page."""
	customers = get_portal_customers()
	loans = get_loans(customers) if customers else []
	accounts = [present_loan(loan, len(customers) > 1) for loan in loans]

	for row in accounts:
		row["url"] = f"/borrower/loan/{row['name']}"

	payload = shell_payload(_("Loan accounts"), _("Apply for a loan"), customers, loans)
	payload.update(labels())
	payload.update(build_summary(loans, get_upcoming_repayments(loans)))
	payload["accounts"] = accounts
	payload["accounts_note"] = (
		_("{0} accounts").format(len(accounts)) if accounts else _("No accounts yet")
	)

	return payload


@frappe.whitelist()
def get_loan_detail() -> dict:
	"""One loan: its terms, its schedule, what was drawn, what it costs to close.

	The loan name arrives from the route, so it is checked against the borrower's own
	customers before it is used. Nothing here trusts the URL.
	"""
	name = frappe.form_dict.get("name")
	if not name:
		raise frappe.PermissionError(_("Not permitted"))

	assert_owns("Loan", name)
	loan = frappe.db.get_value("Loan", name, DETAIL_FIELDS, as_dict=True)

	payload = shell_payload(loan.loan_product, _("Download statement"), [loan.applicant], [loan])
	payload["crumb"] = loan.loan_product
	payload["head_note"] = "{0} · {1}".format(loan.name, STATUS_LABELS.get(loan.status, loan.status))

	payload.update(
		{
			"summary": summary_rows(loan),
			"summary_note": _("{0} at {1}% p.a.").format(
				money(loan.loan_amount), flt(loan.rate_of_interest, 2)
			),
			"schedule": schedule_rows(name),
			"disbursements": disbursement_rows(loan),
			"charges": charge_rows(name),
			"payoff": payoff_rows(name),
		}
	)
	payload.update(card_notes(payload, loan))

	return payload


def summary_rows(loan: dict) -> list[dict]:
	"""The terms, as label and value pairs the page repeats over."""
	drawn = flt(loan.disbursed_amount)
	rows = [
		(_("Sanctioned"), money(loan.loan_amount)),
		(_("Disbursed"), money(drawn)),
		(_("Interest rate"), "{0}% p.a.".format(flt(loan.rate_of_interest, 2))),
		(
			_("Instalment"),
			"{0} · {1}".format(
				money(loan.monthly_repayment_amount),
				(loan.repayment_frequency or "Monthly").lower(),
			),
		),
		(_("Instalments"), str(loan.repayment_periods or "")),
		(_("First due"), long_date(loan.repayment_start_date)),
		(_("Total payable"), money(loan.total_payment)),
		(_("Paid so far"), money(loan.total_amount_paid)),
	]

	if flt(loan.written_off_amount):
		rows.append((_("Written off"), money(loan.written_off_amount)))

	return [{"label": label, "value": value} for label, value in rows]


def current_schedule(loan: str) -> str | None:
	"""The schedule in force. A loan drawn in tranches has several; the Active one rules."""
	active = frappe.db.get_value(
		"Loan Repayment Schedule", {"loan": loan, "docstatus": 1, "status": "Active"}, "name"
	)

	return active or frappe.db.get_value(
		"Loan Repayment Schedule", {"loan": loan, "docstatus": 1}, "name", order_by="creation desc"
	)


def demands_by_instalment(loan: str) -> dict:
	"""What has actually been demanded and settled, keyed by schedule row.

	Loan Demand carries the truth about an instalment. The schedule alone only says
	what was planned, so "paid" is read from the demand, never inferred from a date.
	"""
	index = {}
	rows = frappe.get_all(
		"Loan Demand",
		filters={"loan": loan, "docstatus": 1},
		fields=["repayment_schedule_detail", "demand_amount", "paid_amount", "outstanding_amount"],
		ignore_permissions=True,
	)

	for row in rows:
		if not row.repayment_schedule_detail:
			continue
		entry = index.setdefault(row.repayment_schedule_detail, {"paid": 0.0, "outstanding": 0.0})
		entry["paid"] += flt(row.paid_amount)
		entry["outstanding"] += flt(row.outstanding_amount)

	return index


def instalment_state(row: dict, demands: dict) -> str:
	"""Paid, due or upcoming -- and overdue said plainly, without a risk grade."""
	entry = demands.get(row.name)
	if not entry:
		return _("Upcoming")

	if entry["outstanding"] <= 0:
		return _("Paid")

	return _("Payment overdue") if row.payment_date < nowdate() else _("Due")


def schedule_rows(loan: str) -> list[dict]:
	schedule = current_schedule(loan)
	if not schedule:
		return []

	# Repayment Schedule is a child table with no permission rules of its own, and the
	# parent schedule already belongs to a loan this borrower was proven to own.
	rows = frappe.get_all(
		"Repayment Schedule",
		filters={"parent": schedule, "parenttype": "Loan Repayment Schedule"},
		fields=[
			"name",
			"payment_date",
			"principal_amount",
			"interest_amount",
			"total_payment",
			"balance_loan_amount",
		],
		order_by="payment_date asc",
		ignore_permissions=True,
	)

	demands = demands_by_instalment(loan)

	return [
		{
			"date": short_date(row.payment_date),
			"detail": _("Principal {0} · interest {1}").format(
				money(row.principal_amount), money(row.interest_amount)
			),
			"amount": money(row.total_payment),
			"state": instalment_state(row, demands),
			"balance": _("{0} outstanding after").format(money(row.balance_loan_amount)),
		}
		for row in rows
	]


def disbursement_rows(loan: dict) -> list[dict]:
	"""Drawdowns in order, with the running total. A loan can disburse in parts."""
	rows = frappe.get_all(
		"Loan Disbursement",
		filters={"against_loan": loan.name, "docstatus": 1},
		fields=["disbursement_date", "disbursed_amount", "bank_account"],
		order_by="disbursement_date asc",
	)

	running = 0.0
	presented = []
	for row in rows:
		running += flt(row.disbursed_amount)
		presented.append(
			{
				"date": short_date(row.disbursement_date),
				"amount": money(row.disbursed_amount),
				"detail": row.bank_account or _("Bank account not recorded"),
				"running": _("{0} drawn of {1}").format(money(running), money(loan.loan_amount)),
			}
		)

	return presented


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


def payoff_rows(loan: str) -> list[dict]:
	"""What it costs to close the loan today, broken into its parts.

	PORTAL_PLAN.md section 6.11: show the figure, never take the money. The button
	beside this raises a request for staff.
	"""
	from lending.loan_management.doctype.loan_repayment.loan_repayment import calculate_amounts

	try:
		amounts = calculate_amounts(loan, nowdate(), payment_type="Loan Closure")
	except Exception:
		# A closed or written-off loan has nothing left to price.
		frappe.clear_last_message()
		return []

	parts = [
		(_("Principal"), amounts.get("payable_principal_amount")),
		(_("Interest"), amounts.get("interest_amount")),
		(_("Penalty"), amounts.get("penalty_amount")),
		(_("Charges"), amounts.get("total_charges_payable")),
	]
	rows = [{"label": label, "value": money(value)} for label, value in parts if flt(value)]
	rows.append({"label": _("Payable today"), "value": money(amounts.get("payable_amount"))})

	return rows


def card_notes(payload: dict, loan: dict) -> dict:
	drawn = flt(loan.disbursed_amount)
	undrawn = flt(loan.loan_amount) - drawn
	paid = sum(1 for row in payload["schedule"] if row["state"] == _("Paid"))

	return {
		"schedule_note": (
			_("{0} of {1} instalments paid").format(paid, len(payload["schedule"]))
			if payload["schedule"]
			else _("No schedule yet")
		),
		"disbursements_note": (
			_("{0} undrawn").format(money(undrawn)) if undrawn > 0 else _("Fully drawn")
		),
		"charges_note": (
			_("{0} charges").format(len(payload["charges"]))
			if payload["charges"]
			else _("No charges on this loan")
		),
		"payoff_note": (
			_("As on {0}").format(long_date(nowdate()))
			if payload["payoff"]
			else _("Nothing outstanding")
		),
	}
