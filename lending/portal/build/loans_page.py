# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Loan accounts list as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.loans_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.
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
	NCARD_BODY_STYLES,
	NCARD_HEAD_STYLES,
	NCARD_STAT_STYLES,
	NCARD_STYLES,
	NCARD_TITLE_STYLES,
	NUMBER_STYLES,
	PRIMARY_TEXT_STYLES,
	ROW_STYLES,
	SECONDARY_TEXT_STYLES,
	TABULAR,
	THEAD_LABEL_STYLES,
	THEAD_STYLES,
	badge,
	block,
	bound,
	linked,
	repeater,
)

PAGE_NAME = "Borrower Loan Accounts"
ROUTE = "borrower/loans"
ACTION_HREF = "/apply"

DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal.loans.get_loans_page"))  # noqa: F821
'''


def number_card(title_key, value_key, stat_key, flag_key=None):
	head_children = [bound("span", title_key, styles=NCARD_TITLE_STYLES)]
	if flag_key:
		flag = badge(flag_key, tone="warn")
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
	"""Each row is a link, so the whole line opens that loan rather than a stray word."""
	row = linked(
		"url",
		styles={**ROW_STYLES, "color": "inherit"},
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
				children=[badge("status_label", tone_key="tone")],
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


def content():
	return [
		number_cards(),
		card("Loan accounts", "accounts_note", accounts_body()),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Loan accounts",
		content(),
		action_href=ACTION_HREF,
		data_script=DATA_SCRIPT,
	)
