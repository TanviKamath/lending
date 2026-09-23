# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read-only data for the borrower portal.

A portal page is a definition in the database rather than code, so it cannot import this
module. It reaches these functions by name, through a Studio API Resource pointed at
lending.portal.core.<name> -- the same whitelisted door the Loan Lead server scripts in
install.py use.

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

# The tone the status badge carries, for the statuses that mean something to a borrower
# beyond where in the lifecycle the loan is. A loan being paid as agreed is good news; a
# written-off one is the borrower's to act on. The rest are neither, and say so by
# taking the badge's neutral: a sanctioned loan awaiting disbursement is not a warning.
#
# Nothing here is red. The portal's palette has one danger colour and no shade to lay it
# on, so a status that would be red in the desk takes the warn pair instead.
STATUS_TONES = {
	"Disbursed": "ok",
	"Active": "ok",
	"Written Off": "warn",
}

# What the portal calls itself before a lender has named it. Every page reads the
# name through brand_name(), so this is the only place the words appear.
DEFAULT_BRAND_NAME = "Frappe Lending"

# Every borrower page lives under this prefix, and nothing else in the site's portal
# menu does. It is how nav_items() tells this portal's rows from another's.
PORTAL_ROUTE_PREFIX = "/borrower-portal/"

APPLICATION_STAGES = {
	"Open": "Under review",
	"Approved": "Approved",
	"Rejected": "Not approved",
}

# Under review is the ordinary state of an application and takes the neutral badge. A
# rejection takes warn for the reason STATUS_TONES gives: there is no red to give it.
STAGE_TONES = {
	"Approved": "ok",
	"Rejected": "warn",
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


def days_ago(value) -> str:
	"""How long ago, for an event whose record keeps a date and no time.

	frappe.utils.pretty_date would do this from a timestamp, but these events carry a
	posting date, which it reads as midnight: a repayment entered this morning came out
	as "14 hours ago" and one entered late last night as "yesterday", though both
	happened on the same day.

	Written out rather than composed from a unit and a count because a translator needs
	the whole phrase: the languages this portal is read in do not all pluralise by
	adding an s, and several put the number somewhere else in the sentence.
	"""
	days = -days_until(value)

	if days <= 0:
		return _("Today")
	if days == 1:
		return _("Yesterday")
	if days < 7:
		return _("{0} days ago").format(days)

	if days < 30:
		weeks = days // 7
		return _("1 week ago") if weeks == 1 else _("{0} weeks ago").format(weeks)

	if days < 365:
		months = days // 30
		return _("1 month ago") if months == 1 else _("{0} months ago").format(months)

	years = days // 365

	return _("1 year ago") if years == 1 else _("{0} years ago").format(years)


def loan_url(name: str) -> str:
	"""Where a row about a loan goes when it is pressed.

	Written here rather than at each list that renders one: a row the borrower cannot
	open is a dead end, and four pages were spelling this path out for themselves --
	or, on the overview, not at all.
	"""
	return f"/borrower-portal/loan/{name}" if name else ""


def application_url(name: str) -> str:
	return f"/borrower-portal/application/{name}" if name else ""


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
		**footer_payload(),
		"initials": initials(),
		"holder_name": holder_name(),
		"head_note": head_note(),
		"customer_note": (
			_("{0} customer records").format(len(customers))
			if customers
			else _("No customer record is linked to this login")
		),
		**account_status(loans),
		"crumb": crumb,
		"action_label": action_label,
	}


@frappe.whitelist()
def get_dashboard() -> dict:
	"""Everything the account overview page renders, formatted for display.

	Amounts and dates are formatted here rather than in the page blocks. A block binds a
	value straight into a component prop, so a raw float would render as "317450.0", and
	money is formatted to the company's currency by rules a binding has no access to.
	"""
	customers = get_portal_customers()
	if not customers:
		return empty_dashboard()

	loans = get_loans(customers)
	schedule = get_upcoming_repayments(loans)
	applications = get_applications(customers)
	activity = get_activity(loans)
	accounts = [present_loan(loan, len(customers) > 1) for loan in loans]

	payload = {
		"accounts": accounts,
		"applications": applications,
		"schedule": schedule,
		"activity": activity,
		"accounts_note": (
			_("1 account") if len(accounts) == 1 else _("{0} accounts").format(len(accounts))
		),
		"applications_note": _("{0} in progress").format(len(applications)),
		# The subtitle takes the loan's name when the rows have given it up, so it is
		# still on the card -- once, where a heading belongs -- rather than down it.
		"schedule_note": one_loan_note(_("Next four instalments"), schedule),
		"activity_note": one_loan_note(_("Last 60 days"), activity),
	}
	payload.update(shell_payload(_("Account overview"), _("View payment details"), customers, loans))
	payload.update(labels())
	payload.update(build_summary(loans, schedule))
	payload["tasks"] = waiting_on_borrower(applications)
	payload["tasks_note"] = tasks_note(payload["tasks"])
	payload.update(application_lead(applications))
	# After build_summary, which is what decides whether an instalment is near enough
	# to be anyone's business today. next_flag is empty when none is.
	payload.update(next_action(bool(payload["next_flag"])))

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
		"tasks": [],
		"tasks_note": "",
	}
	payload.update(application_lead([]))
	payload.update(shell_payload(_("Account overview"), _("View payment details"), [], []))
	payload.update(labels())
	payload.update(next_action(due_soon=False))

	return payload


REPAYMENTS_ROUTE = "/borrower-portal/repayments"


def waiting_on_borrower(applications: list[dict]) -> list[dict]:
	"""The rows the borrower has to do something about: their own unsent applications.

	Only applications. An instalment coming due is urgent too, but it already has the
	button under the figures, and a strip that also carried it would put the same
	request on the page twice -- which is the habit this strip was added to break.
	The two divide the work: the strip is what is blocked on the borrower and has
	nowhere else to be said, the button is the payment.

	The rows are shaped like the ones in the Applications table on purpose. The strip
	and the table are two views of the same work, and a borrower should not have to
	notice they are reading different things.
	"""
	return [
		{
			"product": row["product"],
			"note": row["note"] or row["reference"],
			"stage": row["stage"],
			"stage_tone": row["stage_tone"],
			"url": row["url"],
		}
		for row in applications
		if row["needs_borrower"]
	]


def tasks_note(tasks: list[dict]) -> str:
	if not tasks:
		return ""

	return _("1 thing waiting on you") if len(tasks) == 1 else _("{0} things waiting on you").format(len(tasks))


def application_lead(applications: list[dict]) -> dict:
	"""The application the overview's first card stands on: the most recent one open.

	It stands at the top of the page beside the next repayment and the total
	outstanding, because for a borrower who is still applying it is the only one of the
	three that has any news in it -- the other two read "Nothing due" and "No live
	accounts" until the loan is booked.

	An application has no figure, so the card carries words: the product on the line
	where a figure would go, the stage as the badge beside the title, and the name and
	the date it was raised under it. The amount sought is deliberately not here. It is
	in the Application status table below, and it is not the thing a borrower opens this
	page to check -- they know what they asked for, they want to know where it has got
	to.

	The name and the date are two keys rather than the one line the table reads, because
	the card sets them on two lines and a card cannot take a joined string apart.

	Flat keys, one per element, so the card reads a value rather than picking the first
	row out of the applications list in a binding. Which application leads is a decision
	about what a borrower opened the page for, and it belongs here rather than in an
	expression on a block.
	"""
	if not applications:
		return {
			"application_headline": "—",
			"application_stage": "",
			"application_stage_tone": "",
			"application_name": "",
			"application_initiated": "",
			"application_note": _("Nothing in progress"),
			"application_more": "",
			"application_url": "",
		}

	# get_applications orders by posting_date desc, so the first row is the newest.
	first = applications[0]

	return {
		"application_headline": first["product"],
		"application_stage": first["stage"],
		"application_stage_tone": first["stage_tone"],
		"application_name": first["name"],
		"application_initiated": first["initiated"],
		# What is waiting on the borrower, when something is. It used to fall back to
		# the reference, which the card now carries on a line of its own.
		"application_note": first["note"],
		# Only when the card is showing one of several, so the borrower knows the
		# table below holds more than the row they are reading here.
		"application_more": (
			_("{0} in progress").format(len(applications)) if len(applications) > 1 else ""
		),
		# The loan once there is one, the application until then. A card that is about a
		# sanctioned application and opens the form the borrower filled in weeks ago is
		# answering a question they have stopped asking; the account is the answer.
		"application_url": first["loan_url"] or first["url"],
	}


def next_action(due_soon: bool) -> dict:
	"""The button under the figures: always the payment page, not always insisting.

	The destination was never the problem -- a borrower who wants to pay wants this
	page. The emphasis was. A filled black button is a page saying "do this now", and
	it said that every day, including the eighteen days before anything was due, while
	the things that were actually waiting sat further down in grey.

	So the words and the route hold and the weight moves. `action_urgent` is read into
	a data attribute rather than a style because the anchor is one block and cannot
	carry two sets of styles: the quiet variant is a rule in ACTION_TONE_CSS keyed on
	what this puts here. Quiet, the button still offers the payment page; it just
	stops being the loudest thing on a page where nothing is due.
	"""
	return {
		"action_label": _("View payment details"),
		"action_href": REPAYMENTS_ROUTE,
		"action_urgent": "1" if due_soon else "0",
	}


def labels() -> dict:
	"""Static card labels.

	The page data script runs under safe_exec, where str.format and _() are unavailable,
	so every word the blocks render is translated here and shipped flat in the payload.
	A function, not a constant: a module-level _() would resolve once at import.
	"""
	return {
		"label_application": _("Loan application"),
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
	request, so a page cannot be built knowing whether a logo exists. It carries both
	the image and the name, and drops one of them as it renders.

	show_wordmark is the negation of brand_logo. A Studio visibility condition is an
	expression and could invert it, so this is now a convenience rather than a
	necessity -- it was one when the portal's pages could only test a key.
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


def copyright_note() -> str:
	"""The line of ownership at the foot of the page, in the lender's own words.

	A lender that types its own notice gets it verbatim, except for {year}: a notice
	with the year written into it is wrong every January, and nobody edits settings to
	fix that. The substitution is a replace rather than a format so that a notice
	carrying a stray brace is text, not a ValueError on every page of the portal.
	"""
	settings = portal_settings("portal_copyright", "portal_brand_name")
	brand = settings.portal_brand_name or DEFAULT_BRAND_NAME
	year = str(getdate(nowdate()).year)

	written = clean(settings.portal_copyright)
	if written:
		return written.replace("{year}", year)

	# The sentence supplies the stop after the name, so a name that ends in one of its
	# own -- most of them do, being an Ltd. or a Pvt. Ltd. -- does not get two.
	return _("Copyright © {0} {1}. All rights reserved.").format(year, brand.rstrip("."))


def footer_links() -> list[dict]:
	"""The policies a lender publishes, and the address to complain to.

	The rows are a setting read per request and rendered by a repeater, so a lender
	adding a policy needs no rebuild of the pages -- see build.shell.footer. Contact
	us comes last because it is the one link the app supplies itself: a lender is
	required to publish a grievance address, and leaving it to a row someone remembers
	to add would mean the pages that need it most are the ones without it.

	It reads Contact us rather than the address itself. The address is what the link
	does, not what it is for, and a borrower looking for somewhere to complain scans
	the row for the words, not for an @.
	"""
	rows = frappe.get_all(
		"Portal Footer Link",
		filters={"parent": "Lending Settings", "parentfield": "portal_footer_links"},
		fields=["link_label", "url"],
		order_by="idx asc",
	)

	links = [
		{"footer_label": clean(row.link_label), "footer_href": clean(row.url)}
		for row in rows
		if clean(row.link_label) and clean(row.url)
	]

	support = (portal_settings("portal_support_email").portal_support_email or "").strip()
	if support:
		links.append({"footer_label": _("Contact us"), "footer_href": f"mailto:{support}"})

	return links


def footer_payload() -> dict:
	return {"copyright_note": copyright_note(), "footer_links": footer_links()}


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
		"url": loan_url(loan.name),
		"product": loan.loan_product,
		"terms": "{0} · {1}% p.a. · {2} {3}".format(
			loan.name,
			flt(loan.rate_of_interest, 2),
			loan.repayment_periods,
			(loan.repayment_frequency or "Monthly").lower(),
		),
		"status_label": label,
		"tone": STATUS_TONES.get(loan.status, ""),
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
				"url": loan_url(loan_name),
			}
		)

	return name_once(presented)


def one_loan_note(base: str, rows: list[dict]) -> str:
	"""A card's subtitle, carrying the loan's name when its rows have stopped carrying it."""
	products = {row["product"] for row in rows}

	return _("{0} · {1}").format(base, products.pop()) if len(products) == 1 else base


def name_once(rows: list[dict]) -> list[dict]:
	"""Fill each row's two lines, dropping the loan's name when every row shares it.

	A borrower with one loan was reading its name down all four rows of the schedule,
	next to an amount that on a fixed instalment does not move either -- four rows
	saying one thing. Where the rows are all the same loan the name goes up into the
	card's subtitle, said once, and the row leads with what actually changes.

	`product` and `detail` are left on the rows. The notifications panel builds its
	own wording from them, and this is only about what the timeline renders.
	"""
	one_loan = len({row["product"] for row in rows}) == 1

	for row in rows:
		row["title"] = row["detail"] if one_loan else row["product"]
		row["sub"] = "" if one_loan else row["detail"]

	return rows


def build_summary(loans: list[dict], schedule: list[dict]) -> dict:
	live = [loan for loan in loans if is_live(loan)]
	outstanding = sum(outstanding_of(loan) for loan in live)
	sanctioned = sum(flt(loan.loan_amount) for loan in loans)
	undrawn = sum(undrawn_of(loan) for loan in live)
	drawn = sum(flt(loan.disbursed_amount) for loan in live)
	repaid = sum(flt(loan.total_principal_paid) for loan in live)
	first = schedule[0] if schedule else {}
	sanctioned_amount = money(sanctioned)
	sanctioned_note = _("{0} undrawn").format(money(undrawn)) if undrawn else _("Fully drawn")

	return {
		"next_amount": first.get("amount", "—"),
		"next_note": (_("Due {0}").format(first.get("date")) if first else _("Nothing due")),
		"next_flag": next_flag(loans),
		"outstanding": money(outstanding),
		"outstanding_note": (
			_("Across 1 live account")
			if len(live) == 1
			else _("Across {0} live accounts").format(len(live))
		),
		"sanctioned": sanctioned_amount,
		"sanctioned_note": sanctioned_note,
		"sanctioned_line": standing_line(sanctioned, undrawn, drawn, repaid),
	}


def standing_line(sanctioned: float, undrawn: float, drawn: float, repaid: float) -> str:
	"""The one line under the outstanding figure, carrying whatever is not already said.

	The overview folds this in under the figure instead of giving it a card of its own.
	Joined here rather than on the page: which of the four facts is worth saying depends
	on the account, and that is a judgement rather than a layout.

	Which fact it carries depends on the account, because only one of them is ever
	news. Money still undrawn is news: the borrower can draw it. But on a fully drawn
	loan the sanctioned amount is the disbursed amount, which the figure above has
	already given -- the line read "Total sanctioned 3,00,000 · Fully drawn" over an
	outstanding of 3,00,000, and said nothing twice. What that borrower cannot see
	anywhere on the page is how far through it they are, so the line says that.

	Nothing sanctioned is not a figure of zero, and this is the borrower who has
	applied and is waiting: a card said "Total sanctioned 0.00" to them, and the line
	says nothing at all.
	"""
	if not sanctioned:
		return ""

	if undrawn:
		return _("Total sanctioned {0} · {1} undrawn").format(money(sanctioned), money(undrawn))

	if drawn:
		return _("{0} of {1} principal repaid").format(money(repaid), money(drawn))

	return _("Total sanctioned {0} · {1}").format(money(sanctioned), _("Fully drawn"))


def next_flag(loans: list[dict]) -> str:
	rows = upcoming_rows(active_schedule_names([loan.name for loan in loans if is_live(loan)]), limit=1)
	if not rows:
		return ""

	days = days_until(rows[0].payment_date)
	if days <= 0:
		return _("Due today")

	return _("Due in {0} days").format(days) if days <= 7 else ""


def account_status(loans: list[dict]) -> dict:
	"""The badge in the page head: how the borrower's accounts stand, and how loudly.

	Both halves at once, because the tone is the same sentence said in colour: a head
	that reported an overdue payment in the green it uses for a regular account would
	be contradicting itself.
	"""
	live = [loan for loan in loans if is_live(loan)]
	if not live:
		return {"account_status": _("No live accounts"), "account_tone": ""}

	overdue = frappe.db.count(
		"Loan Demand",
		{
			"loan": ["in", [loan.name for loan in live]],
			"docstatus": 1,
			"demand_date": ["<", nowdate()],
			"outstanding_amount": [">", 0],
		},
	)

	if overdue:
		return {"account_status": _("Payment overdue"), "account_tone": "warn"}

	# A borrower with one live account reads its standing in its own row, in the same
	# words and the same green. Saying it again in the head is the page agreeing with
	# itself. With several accounts there is no single row that speaks for all of
	# them, so the sum is worth stating; with one there is nothing to sum.
	if len(live) == 1:
		return {"account_status": "", "account_tone": "ok"}

	return {"account_status": _("All accounts regular"), "account_tone": "ok"}


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


def application_stage(application: dict, needs_borrower: bool, loan: dict | None) -> tuple[str, str]:
	"""Where an application has got to, and the tone its badge carries.

	The two come back together because they are one decision. Split across two
	functions they would be the same three branches written twice, and the day a
	fourth stage is added is the day one of the two copies is forgotten.
	"""
	if needs_borrower:
		return _("Action required"), "warn"

	if loan:
		return _("Loan sanctioned"), "ok"

	return APPLICATION_STAGES.get(application.status, application.status), STAGE_TONES.get(
		application.status, ""
	)


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
		loan = booked.get(row.name)
		stage, stage_tone = application_stage(row, needs_borrower, loan)
		presented.append(
			{
				"name": row.name,
				"url": application_url(row.name),
				# Where a sanctioned application has got to. The application page is the
				# record of the asking; once the loan exists, that account is what the
				# borrower means by the application, and the card leads there instead.
				"loan_url": loan_url(loan.name) if loan else "",
				"product": row.loan_product,
				"reference": "{0} · initiated {1}".format(row.name, long_date(row.posting_date)),
				# The same date as a sentence, for the overview's lead card, which sets
				# it on its own line under the name rather than joined to it.
				"initiated": _("Initiated on {0}").format(long_date(row.posting_date)),
				"stage": stage,
				"stage_tone": stage_tone,
				"needs_borrower": needs_borrower,
				"amount": money(row.loan_amount),
				"note": draft_note(row.name) if needs_borrower else "",
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
				"when": days_ago(row.posting_date),
				"sort": str(getdate(row.posting_date)),
				"title": _("Repayment received"),
				"product": product_of.get(row.against_loan, ""),
				"amount": money(row.amount_paid),
				"url": loan_url(row.against_loan),
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
				"when": days_ago(row.disbursement_date),
				"sort": str(getdate(row.disbursement_date)),
				"title": _("Amount disbursed"),
				"product": product_of.get(row.against_loan, ""),
				"amount": money(row.disbursed_amount),
				"url": loan_url(row.against_loan),
			}
		)

	events.sort(key=lambda event: event["sort"], reverse=True)
	for event in events:
		event.pop("sort", None)

	events = events[:limit]

	# Same rule as the schedule, but the other way up: an event's title already varies
	# -- received, disbursed -- so here it is the rest of the sentence that gives up the
	# loan's name when every event shares one.
	one_loan = len({event["product"] for event in events}) == 1
	for event in events:
		event["sub"] = "" if one_loan else event["product"]
		# The grey half of the sentence beside the dot, joined here so the row is one
		# value rather than three blocks and two separators that each have to know
		# whether their neighbours are empty. The empty parts drop out, so a
		# single-loan list carries no stray separator where the product would be.
		event["note"] = " · ".join(
			part for part in (event["amount"], event["sub"], event["when"]) if part
		)

	return events
