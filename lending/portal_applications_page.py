# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Applications list as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal_applications_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see portal_shell.
"""

from lending.portal_shell import build_page
from lending.portal_theme import (
	AMOUNT_STYLES,
	CARD_HEAD_STYLES,
	CARD_STYLES,
	CARD_SUB_STYLES,
	CARD_TITLE_STYLES,
	COL_AMT_STYLES,
	COL_MAIN_STYLES,
	COL_STATUS_STYLES,
	PRIMARY_TEXT_STYLES,
	ROW_STYLES,
	SECONDARY_TEXT_STYLES,
	STATE_STYLES,
	THEAD_LABEL_STYLES,
	THEAD_STYLES,
	WHY_STYLES,
	block,
	bound,
	linked,
	repeater,
)

PAGE_NAME = "Borrower Applications"
ROUTE = "borrower/applications"
NAV_HREF = "/borrower/applications"
ACTION_HREF = "/apply"

DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal_applications.get_applications_page"))  # noqa: F821
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


def thead(labels):
	columns = [COL_MAIN_STYLES, COL_STATUS_STYLES, COL_AMT_STYLES]
	return block(
		"div",
		styles=THEAD_STYLES,
		children=[
			block("span", styles={**columns[index], **THEAD_LABEL_STYLES}, html=label)
			for index, label in enumerate(labels)
		],
	)


def applications_body():
	"""Each row links to its own tracker, so the whole line is the way in."""
	why = bound("div", "note", styles=WHY_STYLES)
	why["visibilityCondition"] = "note"

	row = linked(
		"url",
		styles={**ROW_STYLES, "color": "inherit"},
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


def content():
	return [card("Applications", "applications_note", applications_body())]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Applications",
		NAV_HREF,
		content(),
		action_href=ACTION_HREF,
		data_script=DATA_SCRIPT,
	)
