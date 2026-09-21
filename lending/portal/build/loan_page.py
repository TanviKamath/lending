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
	COL_AMT_STYLES,
	COL_MAIN_STYLES,
	COL_STATUS_STYLES,
	GRID_STYLES,
	GRID_TABLET_STYLES,
	PRIMARY_TEXT_STYLES,
	ROW_STYLES,
	SECONDARY_TEXT_STYLES,
	STACK_STYLES,
	badge,
	block,
	bound,
	card,
	pair_grid,
	pair_rows,
	repeater,
	timeline_rows,
)

PAGE_NAME = "Borrower Loan Detail"
ROUTE = "borrower/loan/<name>"

DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges. The loan name is not passed from here: get_loan_detail reads it from
# frappe.form_dict server-side and proves the borrower owns it before reading further.
data.update(frappe.call("lending.portal.loans.get_loan_detail"))  # noqa: F821
'''


def summary_card():
	"""The terms, laid across one card the way a form lays out a record.

	These eight figures used to get a number card each. Two things went wrong with
	that. The grid was styled on the repeater's parent, so the repeater itself was the
	only cell and every card came out full width, one under the next -- the rate and
	the first due date ended up a screen apart. And a number card is for a figure that
	stands alone, which none of these do: they are eight readings of one loan, and a
	borrower checking the rate against the instalment wants them within one glance of
	each other rather than stacked down the page.

	pair_grid is the shape the application detail page already gives the same
	question, three to a row, folding to two and then to one.
	"""
	return card("Loan details", "summary_note", pair_grid("summary"))


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
				children=[badge("state", tone_key="state_tone")],
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
		summary_card(),
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
						# No link on these rows: this is already the loan they would open.
						card(
							"Disbursements",
							"disbursements_note",
							timeline_rows("disbursements", "detail", "running"),
						),
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
