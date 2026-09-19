# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds one borrower's loan detail page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.loan_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.

The route carries the loan name. Builder marks a route dynamic when it holds "<",
frappe's router matches it with werkzeug and drops the match into frappe.form_dict,
and the data script runs after that -- so the endpoint reads the name from form_dict
and checks ownership before touching the loan.

PORTAL_PLAN.md section 6.7 shapes this page: summary, schedule, disbursements and
charges, plus the payoff figure from 6.11. No days past due, no NPA flag, no
classification: a borrower sees an overdue instalment, not a risk grade.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import (
	AMOUNT_STYLES,
	BTN_STYLES,
	CARD_HEAD_STYLES,
	CARD_STYLES,
	CARD_SUB_STYLES,
	CARD_TITLE_STYLES,
	CARDS_STYLES,
	COL_AMT_STYLES,
	COL_MAIN_STYLES,
	COL_STATUS_STYLES,
	GRID_STYLES,
	GRID_TABLET_STYLES,
	LI_AMT_STYLES,
	LI_BODY_STYLES,
	LI_DATE_STYLES,
	LI_STYLES,
	NCARD_BODY_STYLES,
	NCARD_HEAD_STYLES,
	NCARD_STYLES,
	NCARD_TITLE_STYLES,
	NUMBER_STYLES,
	PRIMARY_TEXT_STYLES,
	ROW_STYLES,
	SECONDARY_TEXT_STYLES,
	STACK_STYLES,
	STATE_STYLES,
	block,
	bound,
	repeater,
)

PAGE_NAME = "Borrower Loan Detail"
ROUTE = "borrower/loan/<name>"

DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges. The loan name is not passed from here: get_loan_detail reads it from
# frappe.form_dict server-side and proves the borrower owns it before reading further.
data.update(frappe.call("lending.portal.loans.get_loan_detail"))  # noqa: F821
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


def pair_rows(key):
	"""A repeater over label and value pairs: the terms, the charges, the payoff."""
	row = block(
		"div",
		styles=ROW_STYLES,
		children=[
			block(
				"div",
				styles=COL_MAIN_STYLES,
				children=[
					bound("div", "label", styles=SECONDARY_TEXT_STYLES),
					bound("div", "value", styles=PRIMARY_TEXT_STYLES),
				],
			)
		],
	)

	return repeater(key, row)


def summary_body():
	"""The terms, laid out as cards so eight figures stay scannable."""
	row = block(
		"div",
		styles=NCARD_STYLES,
		children=[
			block(
				"div",
				styles=NCARD_HEAD_STYLES,
				children=[bound("span", "label", styles=NCARD_TITLE_STYLES)],
			),
			block(
				"div",
				styles=NCARD_BODY_STYLES,
				children=[bound("div", "value", styles=NUMBER_STYLES)],
			),
		],
	)

	return block("section", styles=CARDS_STYLES, children=[repeater("summary", row)])


def schedule_body():
	row = block(
		"div",
		styles=ROW_STYLES,
		children=[
			block(
				"div",
				styles=COL_MAIN_STYLES,
				children=[
					bound("div", "detail", styles=PRIMARY_TEXT_STYLES),
					bound("div", "balance", styles=SECONDARY_TEXT_STYLES),
				],
			),
			block(
				"div",
				styles=COL_STATUS_STYLES,
				children=[bound("span", "state", styles=STATE_STYLES)],
			),
			block(
				"div",
				styles=COL_AMT_STYLES,
				children=[
					bound("div", "amount", styles=AMOUNT_STYLES),
					bound("div", "date", styles=SECONDARY_TEXT_STYLES),
				],
			),
		],
	)

	return repeater("schedule", row)


def timeline_body(key):
	row = block(
		"div",
		styles=LI_STYLES,
		children=[
			bound("span", "date", styles=LI_DATE_STYLES),
			block(
				"div",
				styles=LI_BODY_STYLES,
				children=[
					bound("div", "detail", styles=PRIMARY_TEXT_STYLES),
					bound("div", "running", styles=SECONDARY_TEXT_STYLES),
				],
			),
			bound("span", "amount", styles=LI_AMT_STYLES),
		],
	)

	return repeater(key, row)


def payoff_body():
	"""The figure, and a request. PORTAL_PLAN.md section 6.11 takes no money here."""
	return block(
		"div",
		children=[
			pair_rows("payoff"),
			block(
				"div",
				styles={"padding": "12px"},
				children=[
					block(
						"a",
						styles=BTN_STYLES,
						html="Request closure",
						attributes={"href": "#"},
					)
				],
			),
		],
	)


def content():
	return [
		summary_body(),
		block(
			"div",
			styles=GRID_STYLES,
			tabletStyles=GRID_TABLET_STYLES,
			children=[
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						card("Repayment schedule", "schedule_note", schedule_body()),
						card("Disbursements", "disbursements_note", timeline_body("disbursements")),
					],
				),
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						card("Payoff amount", "payoff_note", payoff_body()),
						card("Charges", "charges_note", pair_rows("charges")),
					],
				),
			],
		),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Loan",
		content(),
		data_script=DATA_SCRIPT,
	)
