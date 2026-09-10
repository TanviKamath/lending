# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read-only data for the borrower's application list and application detail pages.

Ownership is checked before anything is read, and a application that belongs to
someone else raises the same PermissionError as one that does not exist, so the
portal never confirms a record exists -- PORTAL_PLAN.md section 8.

The tracker is deliberately one function, get_application_steps. Loan Application
carries three statuses today, so it shows three stages plus the loan once booked.
Section 6.6: when Module A reshapes the workflow, that function grows and the page
does not.
"""

import frappe
from frappe import _
from frappe.utils import flt

from lending.portal import (
	APPLICATION_STAGES,
	STATUS_LABELS,
	assert_owns,
	get_applications,
	get_portal_customers,
	long_date,
	money,
	shell_payload,
)

# A step is done, happening now, or still ahead. The marker carries that to the page
# without a conditional style per row.
DONE = ("done", "✓")
CURRENT = ("current", "●")
PENDING = ("pending", "○")

STATE_LABELS = {"done": "Done", "current": "In progress", "pending": "Waiting"}

DETAIL_FIELDS = (
	"name",
	"applicant",
	"applicant_name",
	"applicant_type",
	"status",
	"docstatus",
	"posting_date",
	"loan_product",
	"loan_amount",
	"maximum_loan_amount",
	"repayment_method",
	"repayment_periods",
	"rate_of_interest",
	"is_secured_loan",
	"loan_purpose",
	"total_payable_interest",
	"total_payable_amount",
	"address_line_1",
	"address_line_2",
	"city",
	"state",
	"zip_code",
	"country",
)


@frappe.whitelist()
def get_applications_page() -> dict:
	"""Every application in progress, each linking to its own tracker."""
	customers = get_portal_customers()
	applications = get_applications(customers) if customers else []

	for row in applications:
		row["url"] = f"/borrower/application/{row['name']}"

	waiting = sum(1 for row in applications if row["needs_borrower"])
	payload = shell_payload(_("Applications"), _("Apply for a loan"), customers, [])
	payload.update(
		{
			"applications": applications,
			"applications_note": (
				_("{0} in progress · {1} waiting on you").format(len(applications), waiting)
				if applications
				else _("No applications in progress")
			),
		}
	)

	return payload


@frappe.whitelist()
def get_application_detail() -> dict:
	"""One application: where it stands, what it asks for, who else is on it."""
	name = frappe.form_dict.get("name")
	if not name:
		raise frappe.PermissionError(_("Not permitted"))

	assert_owns("Loan Application", name)
	application = frappe.db.get_value("Loan Application", name, DETAIL_FIELDS, as_dict=True)

	payload = shell_payload(_("Application"), _("Contact us"), [application.applicant], [])
	payload["crumb"] = application.loan_product
	payload["head_note"] = "{0} · {1}".format(
		application.name, stage_label(application)
	)

	documents = document_rows(name)
	payload.update(
		{
			"steps": get_application_steps(application),
			"steps_note": stage_note(application),
			"terms": term_rows(application),
			"terms_note": _("As requested on {0}").format(long_date(application.posting_date)),
			"applicant": applicant_rows(application),
			"applicant_note": _("From your customer record"),
			"co_applicants": co_applicant_rows(name),
			"co_applicants_note": co_applicants_note(name),
			"documents": documents,
			"documents_note": documents_note(documents),
		}
	)

	return payload


def stage_label(application: dict) -> str:
	from lending.portal import application_stage

	return application_stage(application, application.docstatus == 0, booked_loan(application.name))


def booked_loan(application: str) -> dict:
	return (
		frappe.db.get_value(
			"Loan",
			{"loan_application": application, "docstatus": 1},
			["name", "status"],
			as_dict=True,
		)
		or {}
	)


def step(title: str, detail: str, state: tuple) -> dict:
	code, marker = state

	return {
		"title": title,
		"detail": detail,
		"marker": marker,
		"state": _(STATE_LABELS[code]),
	}


def get_application_steps(application: dict) -> list[dict]:
	"""The tracker, as ordered steps.

	Loan Application.status holds Open, Approved and Rejected and nothing else, so the
	honest tracker is three stages: sent, reviewed, decided. A fourth appears once the
	loan is booked. Section 6.6 keeps every page reading this one function.
	"""
	submitted = application.docstatus >= 1
	loan = booked_loan(application.name)
	# A booked loan settles the question whichever way status was left.
	decided = bool(loan) or application.status in ("Approved", "Rejected")
	approved = bool(loan) or application.status == "Approved"

	steps = [
		step(
			_("Application started"),
			_("Initiated {0}").format(long_date(application.posting_date)),
			DONE,
		),
		step(
			_("Your details"),
			_("Received") if submitted else _("Finish and submit your application"),
			DONE if submitted else CURRENT,
		),
		step(
			_("Under review"),
			_("Our team is assessing your application")
			if submitted and not decided
			else (_("Assessed") if decided else _("Starts once you submit")),
			DONE if decided else (CURRENT if submitted else PENDING),
		),
		step(
			_("Decision"),
			_("Approved") if approved else (_("Not approved this time") if decided else _("Awaited")),
			DONE if decided else PENDING,
		),
	]

	if loan:
		steps.append(
			step(
				_("Loan account"),
				"{0} · {1}".format(loan.name, STATUS_LABELS.get(loan.status, loan.status)),
				DONE,
			)
		)

	return steps


def stage_note(application: dict) -> str:
	if application.docstatus == 0:
		return _("Waiting on you")

	if booked_loan(application.name):
		return _("Complete")

	if application.status == "Open":
		return _("Waiting on us")

	return APPLICATION_STAGES.get(application.status, application.status)


def term_rows(application: dict) -> list[dict]:
	rows = [
		(_("Product"), application.loan_product),
		(_("Amount sought"), money(application.loan_amount)),
		(_("Repayment"), application.repayment_method or _("Not chosen")),
		(_("Instalments"), str(application.repayment_periods or "")),
		(_("Interest rate"), "{0}% p.a.".format(flt(application.rate_of_interest, 2))),
		(_("Purpose"), application.loan_purpose or _("Not stated")),
		(_("Security"), _("Secured") if application.is_secured_loan else _("Unsecured")),
	]

	if flt(application.total_payable_amount):
		rows.append((_("Total payable"), money(application.total_payable_amount)))

	return [{"label": label, "value": value} for label, value in rows if value]


def applicant_rows(application: dict) -> list[dict]:
	rows = [
		(_("Name"), application.applicant_name or application.applicant),
		(_("Customer record"), application.applicant),
		(_("Address"), format_address(application) or _("Not on record")),
	]

	return [{"label": label, "value": value} for label, value in rows]


def format_address(application: dict) -> str:
	parts = [
		application.address_line_1,
		application.address_line_2,
		application.city,
		application.state,
		str(application.zip_code) if application.zip_code else "",
		application.country,
	]

	return ", ".join(part for part in parts if part)


def co_applicant_rows(application: str) -> list[dict]:
	"""Whoever else is on the application.

	Loan Co-Applicants carries a name, an email and a mobile number, and nothing more.
	PORTAL_PLAN.md section 6.4 wants relationship, role, income, obligations and a
	consent flag before this is enough for underwriting: those are eight new fields on
	the child doctype, so the page shows what the record actually holds today.
	"""
	rows = frappe.get_all(
		"Loan Co-Applicants",
		filters={"parent": application, "parenttype": "Loan Application"},
		fields=["applicant_name", "applicant_email", "applicant_mobile"],
		ignore_permissions=True,
	)

	return [
		{
			"label": row.applicant_name or _("Unnamed"),
			"value": row.applicant_mobile or "",
			"detail": row.applicant_email or "",
		}
		for row in rows
	]


def co_applicants_note(application: str) -> str:
	count = frappe.db.count(
		"Loan Co-Applicants", {"parent": application, "parenttype": "Loan Application"}
	)

	return _("{0} on this application").format(count) if count else _("Just you")


def document_rows(application: str) -> list[dict]:
	"""The documents actually attached to the application.

	There is no checklist to show against them. Loan Application Document.file is
	mandatory, so an outstanding document is not a row with an empty file -- it is no
	row at all -- and Loan Product names no expected document types, so nothing says
	what is outstanding. PORTAL_PLAN.md section 6.5 wants uploaded against missing, and
	that needs one of those two schema changes first.

	The state still travels as its own key rather than being inferred from the file, so
	the verified and rejected states Module E adds slot in without reshaping the page.
	"""
	rows = frappe.get_all(
		"Loan Application Document",
		filters={"parent": application, "parenttype": "Loan Application"},
		fields=["document_type", "file"],
		ignore_permissions=True,
	)

	return [
		{
			"label": row.document_type or _("Document"),
			"value": _("Uploaded"),
			"marker": "\u2713",
		}
		for row in rows
	]


def documents_note(documents: list[dict]) -> str:
	return (
		_("{0} attached").format(len(documents)) if documents else _("Nothing attached yet")
	)
