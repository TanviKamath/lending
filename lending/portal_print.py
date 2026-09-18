# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower's two downloads: a statement of account, and an interest certificate.

Both reuse the page endpoints in portal_statement rather than querying again. That
matters for more than tidiness: those functions scope every figure to the borrower's
own loans, so reusing them means the PDF cannot show a row the page would not, and
there is only one ownership check to keep correct.

The layout comes from a Print Format record, per PORTAL_PLAN.md section 6.10 -- see
portal_print_formats for why a Print Format is used for something that is not a
document. This module supplies the numbers and turns the rendered HTML into a PDF.

Both endpoints answer with a file rather than JSON, so they are reached by a plain
link on the page rather than by the client script.
"""

import re

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.utils.pdf import get_pdf

from lending.portal import long_date
from lending.portal_print_formats import CERTIFICATE_FORMAT, STATEMENT_FORMAT
from lending.portal_statement import get_certificate_page, get_statement_page

# A filename reaches the browser in a header, so it carries nothing that needs quoting.
UNSAFE_IN_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def render(print_format: str, context: dict) -> str:
	"""The Print Format's own HTML, filled in with this borrower's figures."""
	html = frappe.db.get_value("Print Format", print_format, "html")
	if not html:
		frappe.throw(
			_("The {0} layout is missing. Please ask us to set it up.").format(print_format)
		)

	return frappe.render_template(html, context)


def as_download(html: str, filename: str):
	"""Hand the PDF back as a file. Nothing is returned to the caller after this."""
	frappe.local.response.filename = UNSAFE_IN_FILENAME.sub("-", filename)
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def download_statement():
	"""The statement on screen, as a PDF, for the same period the page is showing.

	The page passes its own filters through in the link, so a borrower looking at
	last quarter downloads last quarter rather than the default period.
	"""
	payload = get_statement_page()
	period = _("{0} to {1}").format(
		long_date(payload["from_date"]), long_date(payload["to_date"])
	)

	html = render(
		STATEMENT_FORMAT,
		{
			"title": _("Statement of account"),
			"subtitle": payload.get("rows_note", ""),
			"brand_name": payload.get("brand_name", ""),
			"brand_logo": payload.get("brand_logo", ""),
			"support_email": payload.get("support_email", ""),
			"holder_name": payload.get("holder_name", ""),
			"period": period,
			"accounts": payload.get("accounts") or [],
			"rows": payload.get("rows") or [],
			"totals": payload.get("totals") or [],
			"generated_on": long_date(nowdate()),
		},
	)

	as_download(html, f"statement-{payload['from_date']}-to-{payload['to_date']}.pdf")


@frappe.whitelist()
def download_certificate():
	"""The interest certificate as a PDF.

	It prints amounts paid and nothing else. Section 6.10 of the plan is explicit:
	no tax figure, no section of the Act, no relief computed. The app holds no tax
	logic, and a wrong number on a document somebody files with their return is a
	real liability.
	"""
	payload = get_certificate_page()

	html = render(
		CERTIFICATE_FORMAT,
		{
			"title": _("Interest certificate"),
			"subtitle": payload.get("rows_note", ""),
			"brand_name": payload.get("brand_name", ""),
			"brand_logo": payload.get("brand_logo", ""),
			"support_email": payload.get("support_email", ""),
			"holder_name": payload.get("holder_name", ""),
			"period": payload.get("year_label", ""),
			"accounts": payload.get("accounts") or [],
			"rows": payload.get("rows") or [],
			"kind": payload.get("kind", ""),
			"disclaimer": payload.get("disclaimer", ""),
			"generated_on": long_date(nowdate()),
		},
	)

	year = (payload.get("year_label") or "").replace(" ", "-").lower()
	as_download(html, f"interest-certificate-{year}.pdf")
