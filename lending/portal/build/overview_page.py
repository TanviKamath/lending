# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower Account overview as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.overview_page.build

Then stop running it. After that run the page is UI-owned: Builder exports every save
to lending/builder_files/, so the exported JSON becomes the source of truth and
re-running this script would discard whatever was laid out on the canvas.

The frame -- rail, sidebar, page head, footer -- is not here. It lives once in the
Builder Component built by shell, and this page references it, so a nav link
fixed on the canvas is fixed for every portal page at once. What follows is only the
content that sits in the frame's middle.

Styling and block helpers come from theme; see its docstring for why every
rule sits on its own block rather than in a stylesheet.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import (
	AMOUNT_STYLES,
	CARD_HEAD_STYLES,
	CARD_STYLES,
	CARD_SUB_STYLES,
	CARD_TITLE_STYLES,
	CARDS_STYLES,
	COL_AMT_STYLES,
	COL_MAIN_STYLES,
	COL_NEXT_STYLES,
	COL_STATUS_STYLES,
	DOT_STYLES,
	FLAG_STYLES,
	GRID_STYLES,
	GRID_TABLET_STYLES,
	LI_AMT_STYLES,
	LI_BODY_STYLES,
	LI_DATE_STYLES,
	LI_STYLES,
	NCARD_BODY_STYLES,
	NCARD_HEAD_STYLES,
	NCARD_STAT_STYLES,
	NCARD_STYLES,
	NCARD_TITLE_STYLES,
	NUMBER_STYLES,
	PRIMARY_TEXT_STYLES,
	ROW_STYLES,
	SECONDARY_TEXT_STYLES,
	STACK_STYLES,
	STATE_STYLES,
	TABULAR,
	THEAD_LABEL_STYLES,
	THEAD_STYLES,
	WHY_STYLES,
	block,
	bound,
	repeater,
)

PAGE_NAME = "Borrower Account Overview"
ROUTE = "borrower/overview"
ACTION_HREF = "/borrower/repayments"

# One call, so the page makes a single trip to the data layer.
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer,
# reached through the whitelisted door the Loan Lead server scripts use.
data.update(frappe.call("lending.portal.core.get_dashboard"))  # noqa: F821
'''


def number_card(title_key, value_key, stat_key, flag_key=None):
	head_children = [bound("span", title_key, styles=NCARD_TITLE_STYLES)]
	if flag_key:
		flag = bound("span", flag_key, styles=FLAG_STYLES)
		flag["visibilityCondition"] = flag_key
		head_children.append(flag)

	return block(
		"div",
		styles=NCARD_STYLES,
		children=[
			block("div", styles=NCARD_HEAD_STYLES, children=head_children),
			block(
				"div",
				styles=NCARD_BODY_STYLES,
				children=[
					bound("div", value_key, styles=NUMBER_STYLES),
					bound("div", stat_key, styles=NCARD_STAT_STYLES),
				],
			),
		],
	)


def number_cards():
	return block(
		"section",
		styles=CARDS_STYLES,
		children=[
			number_card("label_next", "next_amount", "next_note", flag_key="next_flag"),
			number_card("label_outstanding", "outstanding", "outstanding_note"),
			number_card("label_sanctioned", "sanctioned", "sanctioned_note"),
		],
	)


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


def thead(labels):
	columns = [COL_MAIN_STYLES, COL_STATUS_STYLES, COL_NEXT_STYLES, COL_AMT_STYLES]
	return block(
		"div",
		styles=THEAD_STYLES,
		children=[
			block("span", styles={**columns[index], **THEAD_LABEL_STYLES}, html=label)
			for index, label in enumerate(labels)
		],
	)


def accounts_body():
	row = block(
		"div",
		styles=ROW_STYLES,
		children=[
			block(
				"div",
				styles=COL_MAIN_STYLES,
				children=[
					bound("div", "product", styles=PRIMARY_TEXT_STYLES),
					bound("div", "terms", styles=SECONDARY_TEXT_STYLES),
				],
			),
			block(
				"div",
				styles=COL_STATUS_STYLES,
				children=[
					block(
						"span",
						styles=STATE_STYLES,
						children=[
							block("span", styles=DOT_STYLES),
							bound("span", "status_label"),
						],
					)
				],
			),
			block(
				"div",
				styles=COL_NEXT_STYLES,
				children=[
					bound("div", "next_date", styles=TABULAR),
					bound("div", "next_amount", styles=SECONDARY_TEXT_STYLES),
				],
			),
			block(
				"div",
				styles=COL_AMT_STYLES,
				children=[
					bound("div", "outstanding", styles=AMOUNT_STYLES),
					bound("div", "against", styles=SECONDARY_TEXT_STYLES),
				],
			),
		],
	)

	return block(
		"div",
		children=[
			thead(["Account", "Status", "Next repayment", "Outstanding"]),
			repeater("accounts", row),
		],
	)


def applications_body():
	why = bound("div", "note", styles=WHY_STYLES)
	why["visibilityCondition"] = "note"

	row = block(
		"div",
		styles=ROW_STYLES,
		children=[
			block(
				"div",
				styles=COL_MAIN_STYLES,
				children=[
					bound("div", "product", styles=PRIMARY_TEXT_STYLES),
					bound("div", "reference", styles=SECONDARY_TEXT_STYLES),
					why,
				],
			),
			block(
				"div",
				styles=COL_STATUS_STYLES,
				children=[bound("span", "stage", styles=STATE_STYLES)],
			),
			block(
				"div",
				styles=COL_AMT_STYLES,
				children=[bound("div", "amount", styles=AMOUNT_STYLES)],
			),
		],
	)

	return block(
		"div",
		children=[
			thead(["Application", "Stage", "Amount sought"]),
			repeater("applications", row),
		],
	)


def timeline_body(key, title_key):
	row = block(
		"div",
		styles=LI_STYLES,
		children=[
			bound("span", "date", styles=LI_DATE_STYLES),
			block(
				"div",
				styles=LI_BODY_STYLES,
				children=[
					bound("div", title_key, styles=PRIMARY_TEXT_STYLES),
					bound("div", "detail" if title_key == "product" else "sub", styles=SECONDARY_TEXT_STYLES),
				],
			),
			bound("span", "amount", styles=LI_AMT_STYLES),
		],
	)

	return repeater(key, row)


def content():
	"""The page's own blocks, dropped into the shell's content well."""
	return [
		number_cards(),
		block(
			"div",
			styles=GRID_STYLES,
			tabletStyles=GRID_TABLET_STYLES,
			children=[
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						card("Loan accounts", "accounts_note", accounts_body()),
						card("Applications", "applications_note", applications_body()),
					],
				),
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						card("Scheduled repayments", "schedule_note", timeline_body("schedule", "product")),
						card("Recent activity", "activity_note", timeline_body("activity", "title")),
					],
				),
			],
		),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Account overview",
		content(),
		action_href=ACTION_HREF,
		data_script=DATA_SCRIPT,
	)
