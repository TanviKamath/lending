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
brings a borrower here. Everything below it answers "and what did I ask for".
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import (
	AVATAR_STYLES,
	CARD_HEAD_STYLES,
	CARD_STYLES,
	CARD_SUB_STYLES,
	CARD_TITLE_STYLES,
	COL_MAIN_STYLES,
	GRID_STYLES,
	GRID_TABLET_STYLES,
	LI_BODY_STYLES,
	LI_STYLES,
	PRIMARY_TEXT_STYLES,
	ROW_STYLES,
	SECONDARY_TEXT_STYLES,
	STACK_STYLES,
	STATE_STYLES,
	block,
	bound,
	repeater,
)

PAGE_NAME = "Borrower Application Detail"
ROUTE = "borrower/application/<name>"

DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges. The application name is not passed from here: get_application_detail reads
# it from frappe.form_dict server-side and proves ownership before reading further.
data.update(frappe.call("lending.portal.applications.get_application_detail"))  # noqa: F821
'''


def card(title, subtitle_key, body):
	return block(
		"section",
		styles=CARD_STYLES,
		children=[
			block(
				"div",
				styles=CARD_HEAD_STYLES,
				children=[
					block("h2", styles=CARD_TITLE_STYLES, html=title),
					bound("div", subtitle_key, styles=CARD_SUB_STYLES),
				],
			),
			body,
		],
	)


def steps_body():
	"""One row per stage. The marker is a character from the data layer, so a stage
	reads as done, current or waiting without a style per row."""
	row = block(
		"div",
		styles=LI_STYLES,
		children=[
			bound("span", "marker", styles={**AVATAR_STYLES, "background": "transparent"}),
			block(
				"div",
				styles=LI_BODY_STYLES,
				children=[
					bound("div", "title", styles=PRIMARY_TEXT_STYLES),
					bound("div", "detail", styles=SECONDARY_TEXT_STYLES),
				],
			),
			bound("span", "state", styles=STATE_STYLES),
		],
	)

	return repeater("steps", row)


def pair_rows(key, with_detail=False):
	"""A repeater over label and value pairs: terms, applicant, charges, documents."""
	main = [
		bound("div", "label", styles=SECONDARY_TEXT_STYLES),
		bound("div", "value", styles=PRIMARY_TEXT_STYLES),
	]
	if with_detail:
		detail = bound("div", "detail", styles=SECONDARY_TEXT_STYLES)
		detail["visibilityCondition"] = "detail"
		main.append(detail)

	row = block(
		"div",
		styles=ROW_STYLES,
		children=[block("div", styles=COL_MAIN_STYLES, children=main)],
	)

	return repeater(key, row)


def documents_body():
	row = block(
		"div",
		styles=ROW_STYLES,
		children=[
			bound("span", "marker", styles={**AVATAR_STYLES, "background": "transparent"}),
			block(
				"div",
				styles=COL_MAIN_STYLES,
				children=[bound("div", "label", styles=PRIMARY_TEXT_STYLES)],
			),
			bound("span", "value", styles=STATE_STYLES),
		],
	)

	return repeater("documents", row)


def content():
	return [
		card("Where your application stands", "steps_note", steps_body()),
		block(
			"div",
			styles=GRID_STYLES,
			tabletStyles=GRID_TABLET_STYLES,
			children=[
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						card("What you asked for", "terms_note", pair_rows("terms")),
						card("Documents", "documents_note", documents_body()),
					],
				),
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						card("Your details", "applicant_note", pair_rows("applicant")),
						card(
							"Co-applicants",
							"co_applicants_note",
							pair_rows("co_applicants", with_detail=True),
						),
					],
				),
			],
		),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Application",
		content(),
		data_script=DATA_SCRIPT,
	)
