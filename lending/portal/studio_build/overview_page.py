# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower's Account overview, as a Studio page.

It replaces the overview of the Builder portal this one was migrated from, and reads
the same payload: `lending.portal.core.get_dashboard`, unchanged. What differs is what
draws it -- a stage is a frappe-ui Badge rather than a styled span, the record tables
are the List family rather than a grid of divs, and the account's history is
@framework/ui's ActivityTimeline rather than dots and stems drawn by hand.

The scheduled repayments beside it are still a repeater, deliberately: a timeline is a
record of what happened, and those four rows are a diary of what has not.
"""

from lending.portal.studio_build.app import api_resource, upsert_page
from lending.portal.studio_build.blocks import (
	block,
	card,
	click,
	column,
	muted,
	reader,
	record_list,
	repeater,
	row,
	slot,
	spacer,
	stat,
	stat_strip,
	text,
	toned_badge,
	two_columns,
)
from lending.portal.studio_build.shell import frame

TITLE = "Account overview"
ROUTE = "/overview"
SOURCE = "overview"
read = reader(SOURCE)

# The payload's activity rows in the shape ActivityTimeline reads, mapped in the binding
# rather than in the page script.
#
# It has to be the binding. ActivityTimeline declares `activities` required with no
# default and reads `activities.length` on its first line, while Studio's expression
# evaluator answers `undefined` for anything it cannot resolve -- so a binding that can
# be undefined is a crash rather than an empty list. A page-script binding can be
# undefined: an exported page's script is a module the editor loads through the Vite dev
# server, so on a canvas without `bench start` it never arrives, and even in the built
# app it is loaded asynchronously. A data source is there from the first render.
#
# `|| []` is what makes that guarantee hold while the source is still fetching.
#
# `icon` is one of the seven names the gutter knows (see the ui package's
# LUCIDE_ICON_CLASS); anything else falls through to a comment bubble, which is not what
# a repayment is. `type` is deliberately none of the built-in kinds, which is what sends
# every row through the default slot.
ACTIVITY_ROWS = (
	"{{ (%s.data.activity || []).map((entry, index) => ({"
	" type: 'portal', key: 'portal:' + index, icon: 'info',"
	" timestamp: entry.date, data: entry })) }}" % SOURCE
)


def summary():
	"""The three questions a borrower opens the portal with, in one strip.

	The application leads because it is the one with an answer from the first day: the
	two figures beside it read "Nothing due" and "No live accounts" until a loan is
	booked.
	"""
	return stat_strip(
		[
			stat(
				read("label_application"),
				read("application_headline"),
				read("application_note"),
				flag=read("application_stage"),
				flag_tone=f"{SOURCE}.data.application_stage_tone",
				sub=read("application_more"),
			),
			stat(
				read("label_next"),
				read("next_amount"),
				read("next_note"),
				flag=read("next_flag"),
			),
			stat(
				read("label_outstanding"),
				read("outstanding"),
				read("outstanding_note"),
				sub=read("sanctioned_line"),
			),
		]
	)


def tasks():
	"""What is waiting on the borrower, directly under the figures.

	The strip hides itself when the payload has no tasks, so a borrower with nothing to
	do pays nothing for it.
	"""
	task = row(
		[
			column(
				[text("{{ dataItem.product }}", size="text-base"), muted("{{ dataItem.note }}")],
				gap="2px",
			),
			spacer(),
			toned_badge("{{ dataItem.stage }}", "dataItem.stage_tone"),
		],
		gap="10px",
		styles={"padding": "10px 0", "cursor": "pointer"},
		events=click("open(dataItem.url)"),
	)

	return card(
		"Waiting on you",
		read("tasks_note"),
		repeater(read("tasks"), task),
		visible=read("tasks"),
	)


def applications():
	"""The same table the Applications page draws, so a row means the same thing twice."""
	return record_list(
		[("minmax(0, 1fr)", "Application"), ("9rem", "Stage"), ("9rem", "Amount sought")],
		read("applications"),
		[
			[
				text("{{ item.product }}", size="text-base"),
				muted("{{ item.reference }}"),
				muted("{{ item.note }}", visible="{{ item.note }}"),
			],
			[toned_badge("{{ item.stage }}", "item.stage_tone")],
			[text("{{ item.amount }}", size="text-base")],
		],
		script="open(item.url)",
	)


def activity():
	"""The record of the account, on @framework/ui's own ActivityTimeline.

	The Builder page drew this as a repeater over rows, with a dot, a stem and a
	stylesheet rule to cut the stem off the last one -- the one rule it could not put on
	a block, because the rows were one repeated block and only their position told them
	apart. The component owns the axis, so that rule goes with it.

	Its rows are `{type, key, icon, data}` and the portal's are `{title, note, date,
	url, ...}`, so ACTIVITY_ROWS maps between them -- see there for why that mapping is
	a binding rather than a line of the page script.
	"""
	event = row(
		[
			column(
				[text("{{ item.data.title }}", size="text-base"), muted("{{ item.data.note }}")],
				gap="2px",
			),
			spacer(),
			muted("{{ item.data.date }}"),
		],
		gap="10px",
		styles={"width": "100%", "cursor": "pointer"},
		events=click("open(item.data.url)"),
	)

	return block(
		"ActivityTimeline",
		props={"activities": ACTIVITY_ROWS, "loading": "{{ %s.loading }}" % SOURCE},
		slots=slot("default", [event]),
	)


def schedule():
	"""The four instalments coming, as a diary rather than a record."""
	instalment = row(
		[
			muted("{{ dataItem.date }}"),
			column(
				[text("{{ dataItem.title }}", size="text-base"), muted("{{ dataItem.sub }}")],
				gap="2px",
			),
			spacer(),
			text("{{ dataItem.amount }}", size="text-base"),
		],
		gap="10px",
		styles={"padding": "8px 0", "cursor": "pointer"},
		events=click("open(dataItem.url)"),
	)

	return repeater(read("schedule"), instalment, empty="Nothing due")


def content():
	return [
		summary(),
		tasks(),
		two_columns(
			[
				card("Application status", read("applications_note"), applications()),
				card(
					"Activity timeline",
					read("activity_note"),
					activity(),
					visible=read("activity"),
				),
			],
			[
				card(
					"Scheduled repayments",
					read("schedule_note"),
					schedule(),
					visible=read("schedule"),
				)
			],
		),
	]


def build():
	return upsert_page(
		TITLE,
		ROUTE,
		frame(SOURCE, content(), action_label="View payment details", action_route="/borrower/loans"),
		resources=[
			api_resource(SOURCE, "lending.portal.core.get_dashboard"),
			api_resource("alerts", "lending.portal.notifications.get_notifications", auto=0),
		],
	)
