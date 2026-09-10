# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read-only data for the borrower portal.

A Builder page data script runs inside safe_exec, so it cannot import this module.
It reaches these functions with frappe.call("lending.portal.<name>") -- the same door
the Loan Lead server scripts in install.py use.

Every function resolves the borrower's own Customer records first and filters on them.
Nothing here trusts a document name that arrived with the request.
"""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, formatdate, getdate, nowdate

# Internal risk classification. These never reach a borrower -- see PORTAL_PLAN.md
# section 6.7: showing someone their own delinquency labels invites a dispute.
WITHHELD_FROM_BORROWER = (
	"is_npa",
	"manual_npa",
	"days_past_due",
	"classification_code",
	"classification_name",
	"watch_period_end_date",
	"freeze_account",
	"loan_partner",
	"fldg_triggered",
)

LIVE_STATUSES = ("Sanctioned", "Partially Disbursed", "Disbursed", "Active", "Loan Closure Requested")
SETTLED_STATUSES = ("Closed", "Written Off", "Settled")

# Loan.status is a lifecycle field, not a risk grade, so the borrower may see it.
# The wording is softened, the meaning is not.
STATUS_LABELS = {
	"Draft": "Not yet active",
	"Sanctioned": "Sanctioned, awaiting disbursement",
	"Partially Disbursed": "Partly disbursed",
	"Disbursed": "Regular",
	"Active": "Regular",
	"Loan Closure Requested": "Closure requested",
	"Closed": "Closed",
	"Written Off": "Written off",
	"Settled": "Settled",
}

REGULAR_LABELS = ("Regular",)

APPLICATION_STAGES = {
	"Open": "Under review",
	"Approved": "Approved",
	"Rejected": "Not approved",
}


def get_portal_customers() -> list[str]:
	"""Every Customer record that lists the logged-in user in its Portal Users table.

	One login maps to many customers, so this returns a list. See PORTAL_PLAN.md
	section 7: dropping the extra records silently hides a borrower's own loans.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in to view your account."), frappe.PermissionError)

	return frappe.get_all(
		"Customer",
		filters=[["Portal User", "user", "=", user]],
		pluck="name",
	)


def assert_owns(doctype: str, name: str) -> str:
	"""Raise unless the document's applicant is one of the borrower's own customers."""
	applicant = frappe.db.get_value(doctype, name, "applicant")
	if not applicant or applicant not in get_portal_customers():
		raise frappe.PermissionError(_("Not permitted"))

	return applicant


def money(amount) -> str:
	return fmt_money(flt(amount), currency=frappe.defaults.get_global_default("currency") or "INR")


def long_date(value) -> str:
	return formatdate(value, "d MMMM yyyy") if value else ""


def short_date(value) -> str:
	return formatdate(value, "dd MMM yyyy") if value else ""


def days_until(value) -> int:
	return (getdate(value) - getdate(nowdate())).days


@frappe.whitelist()
def get_dashboard() -> dict:
	"""Everything the account overview page renders, formatted for display.

	Amounts and dates are formatted here rather than in the page blocks: Builder binds
	text straight into an element, so a raw float would render as "317450.0".
	"""
	customers = get_portal_customers()
	if not customers:
		return empty_dashboard()

	loans = get_loans(customers)
	schedule = get_upcoming_repayments(loans)
	applications = get_applications(customers)
	accounts = [present_loan(loan, len(customers) > 1) for loan in loans]

	payload = {
		"as_on": long_date(nowdate()),
		"holder_name": holder_name(),
		"initials": initials(),
		"brand_name": brand_name(),
		"crumb": _("Account overview"),
		"action_label": _("View payment details"),
		"head_note": head_note(),
		"customer_note": _("{0} customer records").format(len(customers)),
		"account_status": account_status(loans),
		"accounts": accounts,
		"applications": applications,
		"schedule": schedule,
		"activity": get_activity(loans),
		"accounts_note": _("{0} accounts").format(len(accounts)),
		"applications_note": _("{0} in progress").format(len(applications)),
		"schedule_note": _("Next four instalments"),
		"activity_note": _("Last 60 days"),
	}
	payload.update(labels())
	payload.update(build_summary(loans, schedule))

	return payload


def empty_dashboard() -> dict:
	payload = {
		"as_on": long_date(nowdate()),
		"holder_name": holder_name(),
		"initials": initials(),
		"brand_name": brand_name(),
		"crumb": _("Account overview"),
		"action_label": _("View payment details"),
		"head_note": head_note(),
		"customer_note": _("No customer record is linked to this login"),
		"account_status": _("No accounts found"),
		"accounts": [],
		"applications": [],
		"schedule": [],
		"activity": [],
		"accounts_note": _("Nothing to show"),
		"applications_note": _("Nothing to show"),
		"schedule_note": _("Nothing due"),
		"activity_note": _("No activity"),
		"next_amount": "\u2014",
		"next_note": _("Nothing due"),
		"next_flag": "",
		"outstanding": money(0),
		"outstanding_note": _("No live accounts"),
		"sanctioned": money(0),
		"sanctioned_note": "",
	}
	payload.update(labels())

	return payload


def labels() -> dict:
	"""Static card labels.

	The page data script runs under safe_exec, where str.format and _() are unavailable,
	so every word the blocks render is translated here and shipped flat in the payload.
	A function, not a constant: a module-level _() would resolve once at import.
	"""
	return {
		"label_next": _("Next repayment"),
		"label_outstanding": _("Total outstanding"),
		"label_sanctioned": _("Total sanctioned"),
	}


def holder_name() -> str:
	return frappe.db.get_value("User", frappe.session.user, "full_name") or ""


def head_note() -> str:
	return _("{0} · figures as on {1}").format(holder_name(), long_date(nowdate()))


def initials() -> str:
	"""Two letters for the rail avatar. The page must not hardcode a person."""
	words = (holder_name() or frappe.session.user).split()
	letters = [word[0] for word in words[:2] if word]

	return "".join(letters).upper() or "?"


def brand_name() -> str:
	"""The portal's own name, never a placeholder baked into the blocks.

	PORTAL_PLAN.md section 9 adds Lending Settings.portal_brand_name. The meta check
	keeps this working until that field lands, and starts reading it the moment it does.
	"""
	if frappe.get_meta("Lending Settings").has_field("portal_brand_name"):
		configured = frappe.db.get_single_value("Lending Settings", "portal_brand_name")
		if configured:
			return configured

	return "Frappe Lending"


def get_loans(customers: list[str]) -> list[dict]:
	"""Loans belonging to the borrower. The risk fields are simply never selected."""
	return frappe.get_all(
		"Loan",
		filters={"applicant": ["in", customers], "docstatus": 1},
		fields=[
			"name",
			"applicant",
			"loan_product",
			"status",
			"loan_amount",
			"rate_of_interest",
			"repayment_periods",
			"repayment_frequency",
			"monthly_repayment_amount",
			"disbursed_amount",
			"total_principal_paid",
			"closure_date",
		],
		order_by="status asc, posting_date desc",
	)


def outstanding_of(loan: dict) -> float:
	"""Principal still owed.

	A settled account owes nothing by definition, so it short-circuits: on migrated or
	test data total_principal_paid is not always written back, which would otherwise
	report a closed loan at its full disbursed amount.
	"""
	if loan.status in SETTLED_STATUSES:
		return 0

	return max(flt(loan.disbursed_amount) - flt(loan.total_principal_paid), 0)


def undrawn_of(loan: dict) -> float:
	return max(flt(loan.loan_amount) - flt(loan.disbursed_amount), 0)


def is_live(loan: dict) -> bool:
	return loan.status in LIVE_STATUSES


def present_loan(loan: dict, show_customer: bool) -> dict:
	label = STATUS_LABELS.get(loan.status, loan.status)
	undrawn = undrawn_of(loan)
	next_row = next_repayment_for(loan.name)

	return {
		"name": loan.name,
		"product": loan.loan_product,
		"terms": "{0} · {1}% p.a. · {2} {3}".format(
			loan.name,
			flt(loan.rate_of_interest, 2),
			loan.repayment_periods,
			(loan.repayment_frequency or "Monthly").lower(),
		),
		"status_label": label,
		"is_regular": label in REGULAR_LABELS,
		"customer": loan.applicant if show_customer else "",
		"next_date": short_date(next_row.get("payment_date")) if next_row else "—",
		"next_amount": money(next_row.get("total_payment")) if next_row else "",
		"outstanding": money(outstanding_of(loan)),
		"against": (
			_("{0} undrawn").format(money(undrawn)) if undrawn else _("of {0}").format(money(loan.loan_amount))
		),
		"closed_note": closed_note(loan),
	}


def closed_note(loan: dict) -> str:
	if loan.status not in SETTLED_STATUSES:
		return ""

	if loan.closure_date:
		return _("{0} {1}").format(STATUS_LABELS.get(loan.status, loan.status), short_date(loan.closure_date))

	return STATUS_LABELS.get(loan.status, loan.status)


def active_schedule_names(loan_names: list[str]) -> list[str]:
	if not loan_names:
		return []

	return frappe.get_all(
		"Loan Repayment Schedule",
		filters={"loan": ["in", loan_names], "docstatus": 1, "status": "Active"},
		pluck="name",
	)


def next_repayment_for(loan_name: str) -> dict:
	rows = upcoming_rows(active_schedule_names([loan_name]), limit=1)
	return rows[0] if rows else {}


def upcoming_rows(schedule_names: list[str], limit: int = 4) -> list[dict]:
	"""Future instalments across the given schedules.

	Permissions are skipped deliberately: Repayment Schedule is a child table with no
	permission rules of its own, and schedule_names has already been narrowed to
	schedules of loans this borrower owns.
	"""
	if not schedule_names:
		return []

	return frappe.get_all(
		"Repayment Schedule",
		filters={
			"parent": ["in", schedule_names],
			"parenttype": "Loan Repayment Schedule",
			"payment_date": [">=", nowdate()],
		},
		fields=["parent", "payment_date", "total_payment", "principal_amount", "interest_amount"],
		order_by="payment_date asc",
		limit=limit,
		ignore_permissions=True,
	)


def get_upcoming_repayments(loans: list[dict], limit: int = 4) -> list[dict]:
	live = [loan.name for loan in loans if is_live(loan)]
	product_of = {loan.name: loan.loan_product for loan in loans}
	schedule_to_loan = {
		row.name: row.loan
		for row in frappe.get_all(
			"Loan Repayment Schedule",
			filters={"loan": ["in", live], "docstatus": 1, "status": "Active"},
			fields=["name", "loan"],
		)
	} if live else {}

	rows = upcoming_rows(list(schedule_to_loan), limit=limit)
	presented = []
	for row in rows:
		loan_name = schedule_to_loan.get(row.parent)
		presented.append(
			{
				"date": short_date(row.payment_date),
				"product": product_of.get(loan_name, ""),
				"detail": _("Principal {0} · interest {1}").format(
					money(row.principal_amount), money(row.interest_amount)
				),
				"amount": money(row.total_payment),
			}
		)

	return presented


def build_summary(loans: list[dict], schedule: list[dict]) -> dict:
	live = [loan for loan in loans if is_live(loan)]
	outstanding = sum(outstanding_of(loan) for loan in live)
	sanctioned = sum(flt(loan.loan_amount) for loan in loans)
	undrawn = sum(undrawn_of(loan) for loan in live)
	first = schedule[0] if schedule else {}

	return {
		"next_amount": first.get("amount", "—"),
		"next_note": (
			_("{0} · due {1}").format(first.get("product"), first.get("date")) if first else _("Nothing due")
		),
		"next_flag": next_flag(loans),
		"outstanding": money(outstanding),
		"outstanding_note": _("Across {0} live accounts").format(len(live)),
		"sanctioned": money(sanctioned),
		"sanctioned_note": _("{0} undrawn").format(money(undrawn)) if undrawn else _("Fully drawn"),
	}


def next_flag(loans: list[dict]) -> str:
	rows = upcoming_rows(active_schedule_names([loan.name for loan in loans if is_live(loan)]), limit=1)
	if not rows:
		return ""

	days = days_until(rows[0].payment_date)
	if days <= 0:
		return _("Due today")

	return _("Due in {0} days").format(days) if days <= 7 else ""


def account_status(loans: list[dict]) -> str:
	live = [loan for loan in loans if is_live(loan)]
	if not live:
		return _("No live accounts")

	overdue = frappe.db.count(
		"Loan Demand",
		{
			"loan": ["in", [loan.name for loan in live]],
			"docstatus": 1,
			"demand_date": ["<", nowdate()],
			"outstanding_amount": [">", 0],
		},
	)

	return _("Payment overdue") if overdue else _("All accounts regular")


def get_applications(customers: list[str]) -> list[dict]:
	rows = frappe.get_all(
		"Loan Application",
		filters={"applicant": ["in", customers], "status": "Open", "docstatus": ["<", 2]},
		fields=["name", "loan_product", "loan_amount", "status", "posting_date", "docstatus"],
		order_by="posting_date desc",
	)

	presented = []
	for row in rows:
		needs_borrower = row.docstatus == 0
		presented.append(
			{
				"name": row.name,
				"product": row.loan_product,
				"reference": "{0} · initiated {1}".format(row.name, long_date(row.posting_date)),
				"stage": _("Action required") if needs_borrower else APPLICATION_STAGES.get(row.status, row.status),
				"needs_borrower": needs_borrower,
				"amount": money(row.loan_amount),
				"note": missing_documents_note(row.name) if needs_borrower else "",
				"tag": "you" if needs_borrower else "us",
			}
		)

	return presented


def missing_documents_note(application: str) -> str:
	missing = frappe.get_all(
		"Loan Application Document",
		filters={"parent": application, "parenttype": "Loan Application"},
		fields=["document_type", "file"],
		ignore_permissions=True,
	)
	pending = [row.document_type for row in missing if not row.file]

	return _("{0} still needed").format(", ".join(pending)) if pending else ""


def get_activity(loans: list[dict], limit: int = 5) -> list[dict]:
	loan_names = [loan.name for loan in loans]
	if not loan_names:
		return []

	product_of = {loan.name: loan.loan_product for loan in loans}
	events = []

	for row in frappe.get_all(
		"Loan Repayment",
		filters={"against_loan": ["in", loan_names], "docstatus": 1},
		fields=["against_loan", "posting_date", "amount_paid"],
		order_by="posting_date desc",
		limit=limit,
	):
		events.append(
			{
				"date": short_date(row.posting_date),
				"sort": str(getdate(row.posting_date)),
				"title": _("Repayment received"),
				"sub": product_of.get(row.against_loan, ""),
				"amount": money(row.amount_paid),
			}
		)

	for row in frappe.get_all(
		"Loan Disbursement",
		filters={"against_loan": ["in", loan_names], "docstatus": 1},
		fields=["against_loan", "disbursement_date", "disbursed_amount"],
		order_by="disbursement_date desc",
		limit=limit,
	):
		events.append(
			{
				"date": short_date(row.disbursement_date),
				"sort": str(getdate(row.disbursement_date)),
				"title": _("Amount disbursed"),
				"sub": product_of.get(row.against_loan, ""),
				"amount": money(row.disbursed_amount),
			}
		)

	events.sort(key=lambda event: event["sort"], reverse=True)
	for event in events:
		event.pop("sort", None)

	return events[:limit]
