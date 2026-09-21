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
	ACTIVITY_CSS,
	AMOUNT_STYLES,
	GRID_STYLES,
	GRID_TABLET_STYLES,
	NCARD_BODY_STYLES,
	NCARD_HEAD_STYLES,
	NCARD_STAT_STYLES,
	NCARD_STYLES,
	NCARD_TITLE_STYLES,
	NUMBER_STYLES,
	PRIMARY_TEXT_STYLES,
	SECONDARY_TEXT_STYLES,
	STACK_STYLES,
	TASK_BODY_STYLES,
	TASK_ROW_STYLES,
	TASKS_LIST_STYLES,
	TASKS_NOTE_STYLES,
	TASKS_STYLES,
	TOP_CARDS_STYLES,
	TOP_CARDS_TABLET_STYLES,
	WHY_STYLES,
	activity_list,
	badge,
	block,
	bound,
	card,
	linked,
	record_table,
	repeater,
	timeline_rows,
)

PAGE_NAME = "Borrower Account Overview"
ROUTE = "borrower/overview"

# One call, so the page makes a single trip to the data layer.
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer,
# reached through the whitelisted door the Loan Lead server scripts use.
data.update(frappe.call("lending.portal.core.get_dashboard"))  # noqa: F821
'''


def number_card(title_key, value_key, stat_key, flag_key=None, flag_tone_key=None, sub_key=None):
	"""A single number card: title at the top, large number below, and a stat line.

	Modelled on the number cards the loans page already uses (NCARD_STYLES), so the
	two pages share the same visual language. `flag_key` is the "due in five days"
	pill beside the title, and `sub_key` is the quieter line under the stat.

	`flag_tone_key` is for a pill that does not always mean the same thing. The due
	pill is always a warning and says so on the block; an application stage is a
	warning when it is waiting on the borrower and neutral when it is with the
	lender, so it takes its tone from the payload like a table badge does.
	"""
	head_children = [bound("span", title_key, styles=NCARD_TITLE_STYLES)]
	if flag_key:
		flag = badge(flag_key, tone_key=flag_tone_key) if flag_tone_key else badge(flag_key, tone="warn")
		flag["visibilityCondition"] = flag_key
		head_children.append(flag)

	body_children = [
		bound("div", value_key, styles=NUMBER_STYLES),
		bound("div", stat_key, styles=NCARD_STAT_STYLES),
	]
	if sub_key:
		sub = bound("div", sub_key, styles=NCARD_STAT_STYLES)
		sub["visibilityCondition"] = sub_key
		body_children.append(sub)

	return block(
		"div",
		styles=NCARD_STYLES,
		children=[
			block("div", styles=NCARD_HEAD_STYLES, children=head_children),
			block("div", styles=NCARD_BODY_STYLES, children=body_children),
		],
	)


def summary_block():
	"""The three questions a borrower opens the portal with, in one strip.

	Where has my application got to, what do I pay next, and how much do I still owe.
	The application leads because it is the one that has an answer from the first day:
	the two figures beside it read "Nothing due" and "No live accounts" until a loan is
	booked, and a borrower who is still applying was meeting an empty page.

	Each sits in its own number card -- rounded, bordered, white background -- so the
	overview reads the same way the loans page does. The application card is the wide
	one, because a product name and a stage are words where the other two are figures.
	"""
	return block(
		"section",
		styles=TOP_CARDS_STYLES,
		tabletStyles=TOP_CARDS_TABLET_STYLES,
		children=[
			number_card(
				"label_application",
				"application_headline",
				"application_note",
				flag_key="application_stage",
				flag_tone_key="application_stage_tone",
				sub_key="application_more",
			),
			number_card("label_next", "next_amount", "next_note", flag_key="next_flag"),
			number_card(
				"label_outstanding",
				"outstanding",
				"outstanding_note",
				sub_key="sanctioned_line",
			),
		],
	)


def tasks_block():
	"""What is waiting on the borrower, directly under the figures.

	This is the page's answer to its own worst habit: the only rows that asked
	anything of the borrower were two lines of grey text in the middle of a table,
	under a black button offering a payment that was eighteen days away. The work
	comes first now, and the button follows it.

	The strip hides itself when the payload has no tasks, so it costs a borrower with
	nothing to do exactly nothing.
	"""
	row = linked(
		"url",
		styles=TASK_ROW_STYLES,
		children=[
			block(
				"div",
				styles=TASK_BODY_STYLES,
				children=[
					bound("div", "product", styles=PRIMARY_TEXT_STYLES),
					bound("div", "note", styles=SECONDARY_TEXT_STYLES),
				],
			),
			badge("stage", tone_key="stage_tone"),
		],
	)

	strip = block(
		"section",
		styles=TASKS_STYLES,
		children=[
			bound("div", "tasks_note", styles=TASKS_NOTE_STYLES),
			repeater("tasks", row, styles=TASKS_LIST_STYLES),
		],
	)
	strip["visibilityCondition"] = "tasks"

	return strip


def applications_body():
	"""The same table the Applications page draws, so a row means the same thing twice.

	It matters most for the row that says Action required: that is the only thing on
	this page waiting on the borrower, and until now it was the one row they could
	read but not open.
	"""
	why = bound("div", "note", styles=WHY_STYLES)
	why["visibilityCondition"] = "note"

	return record_table(
		["Application", "Stage", "Amount sought"],
		[
			[
				bound("div", "product", styles=PRIMARY_TEXT_STYLES),
				bound("div", "reference", styles=SECONDARY_TEXT_STYLES),
				why,
			],
			[badge("stage", tone_key="stage_tone")],
			[bound("div", "amount", styles=AMOUNT_STYLES)],
		],
		"applications",
	)


def content():
	"""The page's own blocks, dropped into the shell's content well.

	Three figure cards, then whatever is waiting on the borrower, then two columns:
	the record of the account down the wide side, the four instalments coming down the
	narrow one. The story reads top to bottom on the left -- where the application has
	got to, what it has become, what has happened to it -- and the one thing that is
	about the future sits beside it rather than under it.
	"""
	return [
		summary_block(),
		tasks_block(),
		block(
			"div",
			styles=GRID_STYLES,
			tabletStyles=GRID_TABLET_STYLES,
			children=[
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						# The one card that never hides. A borrower with no loans and
						# no applications still gets this, saying none are in
						# progress, so the page is never only its figures.
						card("Application status", "applications_note", applications_body()),
						card(
							"Activity timeline",
							"activity_note",
							# A line of dots and a sentence each, rather than the dated
							# rows the schedule beside it keeps. What has already
							# happened is read as a record -- "Repayment received,
							# 2 days ago" -- and what has not is read as a diary.
							activity_list("activity", "title", "note", url_key="url", date_key="date"),
							visible_key="activity",
						),
					],
				),
				block(
					"div",
					styles=STACK_STYLES,
					children=[
						card(
							"Scheduled repayments",
							"schedule_note",
							timeline_rows("schedule", "title", "sub", url_key="url"),
							visible_key="schedule",
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
		"Account overview",
		content(),
		action_href=None,
		data_script=DATA_SCRIPT,
		# The one rule the activity list cannot put on a block: its rows are one
		# repeated block, so only a stylesheet can tell the last of them apart and cut
		# the stem that would otherwise run on under the final dot.
		extra_css=ACTIVITY_CSS,
	)
