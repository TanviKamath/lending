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
	MONEY_ACTION_STYLES,
	MONEY_FIGURE_STYLES,
	MONEY_FIGURES_STYLES,
	MONEY_ITEM_STYLES,
	MONEY_LABEL_STYLES,
	MONEY_NOTE_STYLES,
	MONEY_STYLES,
	MONEY_SUB_STYLES,
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


def figure(label_key, value_key, note_key, flag_key=None, sub_key=None):
	"""One of the two figures: what it is, how much it is, and when it falls.

	`flag_key` is the "due in five days" pill that sits beside the label, and `sub_key`
	is the quieter line under the note. Both hide themselves when the payload has
	nothing to put in them, so a borrower with nothing due is not shown an empty pill.
	"""
	label_children = [bound("span", label_key)]
	if flag_key:
		flag = bound("span", flag_key, styles=FLAG_STYLES)
		flag["visibilityCondition"] = flag_key
		label_children.append(flag)

	children = [
		block("div", styles=MONEY_LABEL_STYLES, children=label_children),
		bound("div", value_key, styles=MONEY_FIGURE_STYLES),
		bound("div", note_key, styles=MONEY_NOTE_STYLES),
	]
	if sub_key:
		sub = bound("div", sub_key, styles=MONEY_SUB_STYLES)
		sub["visibilityCondition"] = sub_key
		children.append(sub)

	return block("div", styles=MONEY_ITEM_STYLES, children=children)


def money_block():
	"""The two questions a borrower opens the portal with, and the button that answers.

	The button is the page's own rather than the frame's -- build() passes action_href
	as None, which is how the shell is told to hide its header stub -- because a
	borrower who has just read what is due should not have to look back up to the
	navigation to pay it.
	"""
	return block(
		"section",
		styles=MONEY_STYLES,
		children=[
			block(
				"div",
				styles=MONEY_FIGURES_STYLES,
				children=[
					figure("label_next", "next_amount", "next_note", flag_key="next_flag"),
					figure(
						"label_outstanding",
						"outstanding",
						"outstanding_note",
						sub_key="sanctioned_line",
					),
				],
			),
			bound(
				"a",
				"action_label",
				styles=MONEY_ACTION_STYLES,
				attributes={"href": ACTION_HREF},
			),
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
		money_block(),
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
		# No header button: this page carries its own, under the figure it pays off.
		action_href=None,
		data_script=DATA_SCRIPT,
	)
