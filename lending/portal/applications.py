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

from lending.portal.core import (
	APPLICATION_STAGES,
	STATUS_LABELS,
	assert_owns,
	clean,
	get_applications,
	get_portal_customers,
	leads_for_login,
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
	enquiries = get_enquiries()
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
			"enquiries": enquiries,
			"enquiries_note": (
				_("{0} raised from this website").format(len(enquiries))
				if enquiries
				else _("No enquiries")
			),
		}
	)

	return payload


def get_enquiries() -> list[dict]:
	"""What the borrower asked for before any of it became an application.

	A new borrower has one of these and nothing else, so this is the whole of their
	account on the day they sign up. Each row carries the reference they were given,
	because that is what the public tracker asks for.
	"""
	from lending.portal.apply import tracker_stage

	return [
		{
			"label": row.loan_product,
			"value": money(row.loan_amount),
			"detail": "{0} · {1} · {2}".format(
				row.name, long_date(row.creation), tracker_stage(row)
			),
		}
		for row in leads_for_login()
	]


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
	payload["breadcrumbs"] = [
		{"label": "Applications", "route": "/borrower-portal/applications"},
		{"label": _("Application {0}").format(application.name)}
	]
	payload["head_note"] = "{0} · {1}".format(
		application.name, stage_label(application)
	)

	documents = document_rows(name)
	headline, headline_note = stage_headline(application, booked_loan(name))
	payload.update(
		{
			"product": application.loan_product,
			"reference": _("Application {0}").format(application.name),
			"headline": headline,
			"headline_note": headline_note,
			"steps": get_application_steps(application),
			"steps_note": stage_note(application),
			"preview_note": _("As you sent it on {0}").format(long_date(application.posting_date)),
			"terms": term_rows(application),
			"terms_note": _("The loan you asked for"),
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
	from lending.portal.core import application_stage

	stage, _tone = application_stage(
		application, application.docstatus == 0, booked_loan(application.name)
	)

	return stage


def stage_headline(application: dict, loan: dict) -> tuple[str, str]:
	"""What the tracker adds up to, said once in words: a sentence and its follow-up.

	The steps above it say where the file is. This says what that means for the person
	reading, which is the part they came for. `loan` is passed in rather than read
	again: the caller already has it, and every branch here needs it.

	A refusal is told plainly and without a reason. The reason is a credit decision,
	and PORTAL_PLAN.md section 8 keeps those off the portal -- a borrower asking why
	is a conversation with the team, not a line on a page.
	"""
	if application.docstatus == 0:
		return _("Your application is not sent yet"), _(
			"Finish the details and submit it, and we will start the review."
		)

	if loan:
		return _("Your loan is open"), _("{0} is live. Your schedule and payments are under Loans.").format(
			loan.name
		)

	if application.status == "Approved":
		return _("Congratulations!"), _(
			"Your loan has been approved. We will get in touch with you about the disbursal."
		)

	if application.status == "Rejected":
		return _("Not approved this time"), _(
			"We could not approve this application. Contact us and we will talk it through."
		)

	return _("With our team"), _("We are assessing your application and will come back to you.")


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


def step(title: str, detail: str, state: tuple, short: str = "") -> dict:
	code, marker = state

	return {
		"title": title,
		"detail": detail,
		"marker": marker,
		"state": _(STATE_LABELS[code]),
		# What the stage is called where the tracker runs across the page rather than
		# down it: five titles side by side break into two lines each, and the title is
		# a phrase where the space allows only a word.
		"short": short or title,
		# The label above is translated for reading. The code is what a reader compares
		# against, so finding the step in progress does not depend on the language.
		"code": code,
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
			_("Started"),
		),
		step(
			_("Your details"),
			_("Received") if submitted else _("Finish and submit your application"),
			DONE if submitted else CURRENT,
			_("Details"),
		),
		step(
			_("Under review"),
			_("Our team is assessing your application")
			if submitted and not decided
			else (_("Assessed") if decided else _("Starts once you submit")),
			DONE if decided else (CURRENT if submitted else PENDING),
			_("Review"),
		),
		step(
			_("Decision"),
			_("Approved") if approved else (_("Not approved this time") if decided else _("Awaited")),
			DONE if decided else PENDING,
			_("Decision"),
		),
	]

	if loan:
		steps.append(
			step(
				_("Loan account"),
				"{0} · {1}".format(loan.name, STATUS_LABELS.get(loan.status, loan.status)),
				DONE,
				_("Loan"),
			)
		)

	return steps


def progress_line(steps: list[dict]) -> str:
	"""Where a tracker has reached, in one line: "Step 3 of 4 - Under review".

	A page with room for a timeline draws the steps. A page with room for a line says
	which one of them the application is standing on, which is the part a borrower
	checking in actually wants.
	"""
	at = next(
		(index for index, row in enumerate(steps) if row["code"] == "current"), len(steps) - 1
	)

	return _("Step {0} of {1} · {2}").format(at + 1, len(steps), steps[at]["title"])


def progress_by_application(names: list[str]) -> dict[str, str]:
	"""One progress line per application, read in a single query.

	The names come from the borrower's own list, never from the request, so this reads
	them without a second ownership check.
	"""
	if not names:
		return {}

	rows = frappe.get_all(
		"Loan Application",
		filters={"name": ["in", names]},
		fields=["name", "status", "docstatus", "posting_date"],
	)

	return {row.name: progress_line(get_application_steps(row)) for row in rows}


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


@frappe.whitelist()
def get_documents_page() -> dict:
	"""Every document attached to any of the borrower's applications.

	There is no checklist to show against them, for the reason document_rows() gives:
	an outstanding document is not a row with an empty file, it is no row at all, and
	nothing records what a product expects. So this page answers "what have I sent
	you" honestly, and cannot yet answer "what do you still need".
	"""
	customers = get_portal_customers()
	applications = get_applications(customers) if customers else []

	progress = progress_by_application([row["name"] for row in applications])

	documents = []
	listed = []
	for application in applications:
		attached = document_rows(application["name"])
		documents.extend({**document, "detail": application["product"]} for document in attached)
		listed.append(
			{
				**application,
				"progress": progress.get(application["name"], ""),
				# This page is about files, so the column that carries money elsewhere
				# counts what the application already holds.
				"attached": (
					_("{0} sent").format(len(attached)) if attached else _("Nothing sent")
				),
			}
		)

	payload = shell_payload(_("Documents"), _("Contact us"), customers, [])
	payload.update(
		{
			"documents": documents,
			"documents_note": (
				_("{0} attached across {1} applications").format(len(documents), len(applications))
				if documents
				else _("Nothing attached yet")
			),
			"applications": listed,
			"applications_note": (
				_("{0} in progress · tap one to see its tracker").format(len(applications))
				if applications
				else _("No applications in progress")
			),
			# The wording that went with having no upload form at all. Both notes are
			# returned; the page shows whichever fits, on can_upload.
			"upload_note": _("Attach it to one of your applications. Only you and we can see it."),
			"no_upload_note": _(
				"There is no application open for new documents just now. "
				"Once we have your application in draft, you can attach files here."
			),
		}
	)

	return payload


# --- the one write this page accepts ------------------------------------------------

# A borrower sends identity and income papers, so images and PDFs and nothing else.
# Checked on the extension here and again by the File doctype's own rules.
ALLOWED_DOCUMENT_TYPES = (".pdf", ".png", ".jpg", ".jpeg")

# Comfortably above a phone photo of a payslip, well below anything worth hosting.
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024


@frappe.whitelist()
def get_document_choices() -> dict:
	"""What the upload form offers: which application, and which kind of document."""
	customers = get_portal_customers()
	applications = get_applications(customers) if customers else []

	# Only a draft may take a new document. A submitted application is with our team,
	# and PORTAL_PLAN.md section 6.2 keeps the borrower out of it from that point.
	open_applications = [
		{"label": f"{row['name']} · {row['product']}", "value": row["name"]}
		for row in applications
		if row.get("needs_borrower")
	]

	return {
		"application_options": open_applications,
		"document_type_options": [
			{"label": row, "value": row}
			for row in frappe.get_all("Loan Document Type", pluck="name", order_by="name asc")
		],
		"can_upload": bool(open_applications),
		"upload_label": _("Send this document"),
	}


def editable_application() -> str:
	"""The application the upload names, if the borrower owns it and may still edit it."""
	name = clean(frappe.form_dict.get("application"))
	if not name:
		raise frappe.PermissionError(_("Not permitted"))

	assert_owns("Loan Application", name)

	if frappe.db.get_value("Loan Application", name, "docstatus") != 0:
		frappe.throw(
			_("This application is with our team now, so it cannot take new documents."),
			frappe.ValidationError,
		)

	return name


def read_upload():
	"""The uploaded file, checked before anything is written.

	frappe.request.files is where a multipart upload lands. The checks are on the
	bytes we hold, not on what the browser said: an accept attribute on the input is
	a hint to the file picker and nothing more.
	"""
	upload = (frappe.request.files or {}).get("file") if frappe.request else None
	if not upload:
		frappe.throw(_("Please choose a file."), frappe.ValidationError)

	content = upload.stream.read()
	if not content:
		frappe.throw(_("That file is empty."), frappe.ValidationError)

	if len(content) > MAX_DOCUMENT_BYTES:
		frappe.throw(
			_("Please keep the file under {0} MB.").format(MAX_DOCUMENT_BYTES // (1024 * 1024)),
			frappe.ValidationError,
		)

	filename = clean(upload.filename)
	if not filename.lower().endswith(ALLOWED_DOCUMENT_TYPES):
		frappe.throw(
			_("Please send a PDF or a photo ({0}).").format(", ".join(ALLOWED_DOCUMENT_TYPES)),
			frappe.ValidationError,
		)

	return filename, content


@frappe.whitelist(methods=["POST"])
def upload_document() -> dict:
	"""Attach one document to one of the borrower's own draft applications.

	Written with ignore_permissions for the reason save_profile gives: a Website User
	holds no write rights on Loan Application, and granting them would open every
	other borrower's applications too. The narrowing happens above instead.

	The file is private. A loan document is a payslip or an identity paper, and a
	public file URL is guessable by anyone who has seen one.
	"""
	application = editable_application()
	document_type = clean(frappe.form_dict.get("document_type"))

	if not frappe.db.exists("Loan Document Type", document_type):
		frappe.throw(_("Please choose a document type from the list."), frappe.ValidationError)

	filename, content = read_upload()

	stored = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Loan Application",
			"attached_to_name": application,
		}
	).insert(ignore_permissions=True)

	document = frappe.get_doc("Loan Application", application)
	document.append("documents", {"document_type": document_type, "file": stored.file_url})
	document.save(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep

	return {
		"headline": _("Received"),
		"message": _("{0} has been added to {1}.").format(document_type, application),
		"offer": [],
		"reference_note": "",
	}
