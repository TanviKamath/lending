# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read-only data for the borrower portal.

A Builder page data script runs inside safe_exec, so it cannot import this module.
It reaches these functions with frappe.call("lending.portal.core.<name>") -- the same door
the Loan Lead server scripts in install.py use.

Every function resolves the borrower's own Customer records first and filters on them.
Nothing here trusts a document name that arrived with the request.
"""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, formatdate, getdate, nowdate
from frappe.website.utils import get_portal_sidebar_items

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

# What the portal calls itself before a lender has named it. Every page reads the
# name through brand_name(), so this is the only place the words appear.
DEFAULT_BRAND_NAME = "Frappe Lending"

# Every borrower page lives under this prefix, and nothing else in the site's portal
# menu does. It is how nav_items() tells this portal's rows from another's.
PORTAL_ROUTE_PREFIX = "/borrower/"

APPLICATION_STAGES = {
	"Open": "Under review",
	"Approved": "Approved",
	"Rejected": "Not approved",
}


def assert_portal_enabled():
	if not frappe.db.get_single_value("Lending Settings", "enable_borrower_portal"):
		raise frappe.PageDoesNotExistError


def assert_public_apply_enabled():
	assert_portal_enabled()

	if not frappe.db.get_single_value("Lending Settings", "enable_public_apply"):
		raise frappe.PageDoesNotExistError


def get_portal_customers() -> list[str]:
	assert_portal_enabled()

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


def clean(value) -> str:
	return frappe.utils.strip_html(str(value or "")).strip()


def money(amount) -> str:
	return fmt_money(flt(amount), currency=frappe.defaults.get_global_default("currency") or "INR")


def long_date(value) -> str:
	return formatdate(value, "d MMMM yyyy") if value else ""


def short_date(value) -> str:
	return formatdate(value, "dd MMM yyyy") if value else ""


def days_until(value) -> int:
	return (getdate(value) - getdate(nowdate())).days


def current_route() -> str:
	"""The route being served, spelt the way a menu row spells its own.

	frappe.local rather than frappe.request: off a request the proxy has nothing behind
	it, and asking it for a path raises rather than answering. Off a request no row is
	the current one and the sidebar simply has nothing lit.
	"""
	request = getattr(frappe.local, "request", None)

	return "/" + (getattr(request, "path", "") or "").strip("/")


def is_current(item: dict, route: str) -> bool:
	"""Whether a menu row owns the route being served.

	A row owns its own route, and the section named by its `covers` key. The trailing
	slash is what keeps /borrower/applications out of the hands of /borrower/application.
	"""
	if route == item.get("route"):
		return True

	covers = item.get("covers")

	return bool(covers) and route.startswith(covers + "/")


def nav_items() -> list[dict]:
	"""The sidebar rows, read from Frappe's portal menu and marked for this page.

	get_portal_sidebar_items() answers for every portal on the site at once, so an
	ERPNext bench hands back Orders and Invoices alongside these. The borrower frame
	takes the rows under its own prefix and leaves the rest to the portal they were
	written for.
	"""
	route = current_route()

	return [
		{
			"nav_title": _(item.get("title") or item.get("label") or ""),
			"nav_route": item.get("route"),
			# Read into aria-current, which is both what a screen reader announces and
			# what the stylesheet marks the row with.
			"nav_current": "page" if is_current(item, route) else "false",
		}
		for item in get_portal_sidebar_items()
		if (item.get("route") or "").startswith(PORTAL_ROUTE_PREFIX)
	]


def shell_payload(crumb: str, action_label: str, customers: list[str], loans: list[dict]) -> dict:
	return {
		"as_on": long_date(nowdate()),
		"nav_items": nav_items(),
		**brand_payload(),
		"initials": initials(),
		"holder_name": holder_name(),
		"head_note": head_note(),
		"customer_note": (
			_("{0} customer records").format(len(customers))
			if customers
			else _("No customer record is linked to this login")
		),
		"account_status": account_status(loans),
		"crumb": crumb,
		"action_label": action_label,
	}


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
		"accounts": accounts,
		"applications": applications,
		"schedule": schedule,
		"activity": get_activity(loans),
		"accounts_note": _("{0} accounts").format(len(accounts)),
		"applications_note": _("{0} in progress").format(len(applications)),
		"schedule_note": _("Next four instalments"),
		"activity_note": _("Last 60 days"),
	}
	payload.update(shell_payload(_("Account overview"), _("View payment details"), customers, loans))
	payload.update(labels())
	payload.update(build_summary(loans, schedule))

	return payload


def empty_dashboard() -> dict:
	payload = {
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
		# Nothing sanctioned is not a figure of zero. The line hides itself rather than
		# telling a borrower with no loans that they have been sanctioned nothing.
		"sanctioned_line": "",
	}
	payload.update(shell_payload(_("Account overview"), _("View payment details"), [], []))
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


def portal_settings(*fieldnames) -> frappe._dict:
	"""The Borrower Portal section of Lending Settings, by fieldname.

	One door onto the settings, so the fallback for an unset field is decided once
	rather than at each of the dozen places that read one.
	"""
	return frappe._dict(
		{name: frappe.db.get_single_value("Lending Settings", name) for name in fieldnames}
	)


def brand_name() -> str:
	"""The portal's own name, never a placeholder baked into the blocks."""
	return portal_settings("portal_brand_name").portal_brand_name or DEFAULT_BRAND_NAME


def brand_payload() -> dict:
	"""The lender's mark and its grievance address, for every frame that carries one.

	The pages are written once by the build scripts and these values are read per
	request, so the page cannot be built knowing whether a logo exists. It carries
	both the image and the name, and drops one of them as it renders -- see
	build.theme.brand_lockup. show_wordmark is the negation of brand_logo, spelt out
	here because a Builder visibility condition tests a key and cannot invert it.
	"""
	settings = portal_settings("portal_brand_name", "portal_logo", "portal_support_email")
	logo = (settings.portal_logo or "").strip()
	support = (settings.portal_support_email or "").strip()

	return {
		"brand_name": settings.portal_brand_name or DEFAULT_BRAND_NAME,
		"brand_logo": logo,
		"show_wordmark": 0 if logo else 1,
		"support_email": support,
		"support_href": f"mailto:{support}" if support else "#",
	}


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


def status_label(loan: dict) -> str:
	"""A loan's lifecycle status, in the words a borrower is meant to read.

	Read from more than one page now, and a raw Loan.status leaking onto one of them is
	exactly the wording PORTAL_PLAN.md section 6.7 is careful about.
	"""
	return STATUS_LABELS.get(loan.status, loan.status)


def present_loan(loan: dict, show_customer: bool) -> dict:
	label = status_label(loan)
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
	sanctioned_amount = money(sanctioned)
	sanctioned_note = _("{0} undrawn").format(money(undrawn)) if undrawn else _("Fully drawn")

	return {
		"next_amount": first.get("amount", "—"),
		"next_note": (
			_("{0} · due {1}").format(first.get("product"), first.get("date")) if first else _("Nothing due")
		),
		"next_flag": next_flag(loans),
		"outstanding": money(outstanding),
		"outstanding_note": _("Across {0} live accounts").format(len(live)),
		"sanctioned": sanctioned_amount,
		"sanctioned_note": sanctioned_note,
		# The overview folds the sanctioned amount into one line under the outstanding
		# figure instead of giving it a card of its own. Joined here rather than on the
		# page because Builder binds one key straight into one element, and the page
		# data script runs under safe_exec, where str.format is unavailable.
		#
		# Nothing sanctioned is not a figure of zero, and this is the borrower who has
		# applied and is waiting: a card said "Total sanctioned ₹0.00" to them, and the
		# line says nothing at all. The card's own two keys are left as they were, since
		# the loan accounts page still shows them.
		"sanctioned_line": (
			_("Total sanctioned {0} · {1}").format(sanctioned_amount, sanctioned_note) if sanctioned else ""
		),
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


def loans_by_application(applications: list[str]) -> dict:
	"""The loan booked against each application, in one query.

	Loan Application.status is left at Open when create_loan books the loan, so the
	status field alone would report a disbursed borrower as still under review. The
	loan is the stronger evidence, so every stage decision consults it.
	"""
	if not applications:
		return {}

	rows = frappe.get_all(
		"Loan",
		filters={"loan_application": ["in", applications], "docstatus": 1},
		fields=["name", "status", "loan_application"],
	)

	return {row.loan_application: row for row in rows}


def application_stage(application: dict, needs_borrower: bool, loan: dict | None) -> str:
	if needs_borrower:
		return _("Action required")

	if loan:
		return _("Loan sanctioned")

	return APPLICATION_STAGES.get(application.status, application.status)


def leads_for_login() -> list[dict]:
	"""Enquiries raised under this login's own email address.

	A Loan Lead carries no Customer -- it exists before anyone becomes one -- so email
	is the only join there is. It is the session's own address, never a value from the
	request, so this can only ever return enquiries raised with the address the
	borrower signs in with.

	This is what a brand new borrower has instead of loans. Without it they open an
	account, log in, and are told there is nothing here.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in to view your account."), frappe.PermissionError)

	return frappe.get_all(
		"Loan Lead",
		filters={"email": user, "docstatus": ["<", 2]},
		fields=[
			"name",
			"applicant_name",
			"loan_product",
			"loan_amount",
			"status",
			"prequalification_status",
			"creation",
		],
		order_by="creation desc",
	)


def get_applications(customers: list[str]) -> list[dict]:
	rows = frappe.get_all(
		"Loan Application",
		filters={"applicant": ["in", customers], "status": "Open", "docstatus": ["<", 2]},
		fields=["name", "loan_product", "loan_amount", "status", "posting_date", "docstatus"],
		order_by="posting_date desc",
	)

	booked = loans_by_application([row.name for row in rows])

	presented = []
	for row in rows:
		needs_borrower = row.docstatus == 0
		presented.append(
			{
				"name": row.name,
				"product": row.loan_product,
				"reference": "{0} · initiated {1}".format(row.name, long_date(row.posting_date)),
				"stage": application_stage(row, needs_borrower, booked.get(row.name)),
				"needs_borrower": needs_borrower,
				"amount": money(row.loan_amount),
				"note": draft_note(row.name) if needs_borrower else "",
				"tag": "you" if needs_borrower else "us",
			}
		)

	return presented


def draft_note(application: str) -> str:
	"""Why a draft application is waiting on the borrower.

	This used to list the documents still needed, which it could never do:
	Loan Application Document.file is mandatory, so a row without a file cannot be
	saved, and Loan Product names no expected document types. A checklist needs one
	of those two to change -- see PORTAL_PLAN.md section 6.5 -- so until then the note
	says the one thing that is true of every draft.
	"""
	uploaded = frappe.db.count(
		"Loan Application Document", {"parent": application, "parenttype": "Loan Application"}
	)

	return (
		_("Submit to start the review · {0} documents attached").format(uploaded)
		if uploaded
		else _("Submit to start the review")
	)


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
