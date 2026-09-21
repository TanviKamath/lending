# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds one borrower's application detail page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.application_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.

The route carries the application name. Builder marks a route dynamic when it holds
"<", frappe's router matches it with werkzeug and drops the match into
frappe.form_dict, and the data script runs after that -- so the endpoint reads the
name from form_dict and checks ownership before touching the record.

The tracker leads, because "where has my application got to" is the question that
brings a borrower here. It runs across the hero rather than down a card, so the whole
journey is one glance, and under it a sentence says what the stage it has reached
means. Everything below answers "and what did I ask for", in one card whose sections
are tabs: four sets of label-and-value pairs stacked down the page is a scroll, and
only one of them is being read at a time.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import (
	APPLICATION_CSS,
	AS_ON_STYLES,
	BACK_STYLES,
	CHEVRON_LEFT,
	CREST_STYLES,
	ICON_MONEY,
	block,
	bound,
	lead_card,
	pair_grid,
	preview,
)

PAGE_NAME = "Borrower Application Detail"
ROUTE = "borrower/application/<name>"

DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges. The application name is not passed from here: get_application_detail reads
# it from frappe.form_dict server-side and proves ownership before reading further.
data.update(frappe.call("lending.portal.applications.get_application_detail"))  # noqa: F821
'''

def crest():
	"""The way back, and the day this is being read.

	Both sit above the hero rather than in the shell's own header: the header is one
	component shared by eleven pages, and a node added there is only served after all
	eleven have been rebuilt.
	"""
	return block(
		"div",
		styles=CREST_STYLES,
		children=[
			block(
				"a",
				styles=BACK_STYLES,
				attributes={"href": "/borrower/applications"},
				children=[
					block("span", html=CHEVRON_LEFT, attributes={"aria-hidden": "true"}),
					block("span", html="Back"),
				],
			),
			bound("span", "as_on", styles=AS_ON_STYLES),
		],
	)


def sections():
	"""What the preview holds, in the order a borrower checks it: the loan first,
	because that is what the application is, then who it is for, then what went with
	it. Built per call, so no two pages share a block dict."""
	return [
		("terms", "Loan Details", "terms_note", pair_grid("terms")),
		("applicant", "Your Details", "applicant_note", pair_grid("applicant")),
		("co_applicants", "Co-applicants", "co_applicants_note", pair_grid("co_applicants", with_detail=True)),
		("documents", "Documents", "documents_note", pair_grid("documents", marker=True)),
	]


def content():
	return [
		crest(),
		lead_card("product", "reference", "steps", "headline", "headline_note", ICON_MONEY),
		preview("Application preview", "preview_note", sections()),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Application",
		content(),
		data_script=DATA_SCRIPT,
		extra_css=APPLICATION_CSS,
	)
