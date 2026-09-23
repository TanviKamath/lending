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
from lending.portal.studio_build.application_pages import applications
from lending.portal.studio_build.blocks import (
	block,
	card,
	chevron,
	click,
	column,
	icon_line,
	muted,
	reader,
	record_stat,
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
# Where every figure on this page is answered in full, and so where the head's button
# and the two figure cards all lead.
ACCOUNTS_ROUTE = "/loans"
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


def application_card():
	"""The newest open application, as the record it is rather than as a figure.

	It sits in a strip of numbers and is not one. The product name is a headline at the
	weight of a heading, the application's own name and the day it was raised are the
	two quiet lines under it, and the tile on the left carries the stage's colour the
	way the badge at the top does. What is waiting on the borrower, and how many more
	applications the table below holds, follow only when there is something to say.
	"""
	stage_tone = f"{SOURCE}.data.application_stage_tone"
	# The label, the stage, and the chevron at the end of the line the two figure cards
	# put theirs on. The chevron waits for a destination: a borrower with nothing in
	# progress reads the same card saying so, and that one opens nothing.
	label = row(
		[
			muted(read("label_application")),
			toned_badge(read("application_stage"), stage_tone, visible=read("application_stage")),
			spacer(),
			chevron(visible=read("application_url")),
		],
		gap="8px",
	)
	initiated = icon_line(
		"calendar", read("application_initiated"), visible=read("application_initiated")
	)

	return record_stat(
		"file-text",
		stage_tone,
		[
			label,
			text(
				read("application_headline"),
				tag="div",
				size="text-2xl",
				styles={"fontWeight": "600", "padding": "2px 0"},
			),
			muted(read("application_name"), visible=read("application_name")),
			initiated,
			muted(read("application_note"), visible=read("application_note")),
			muted(read("application_more"), visible=read("application_more")),
		],
		script=f"open({SOURCE}.data.application_url)",
	)


def summary():
	"""The three questions a borrower opens the portal with, in one strip.

	The application leads because it is the one with an answer from the first day: the
	two figures beside it read "Nothing due" and "No live accounts" until a loan is
	booked.

	Both figures are answered on the loan accounts page -- the instalment in its Next
	repayment column, the balance in its Outstanding one -- so both cards open it. The
	overview is a summary, and a summary that cannot be opened makes a borrower hunt
	down the rail for the page the figure came from.
	"""
	return stat_strip(
		[
			application_card(),
			stat(
				read("label_next"),
				read("next_amount"),
				read("next_note"),
				flag=read("next_flag"),
				icon_name="calendar",
				note_icon="calendar",
				script=f"open('{ACCOUNTS_ROUTE}')",
			),
			stat(
				read("label_outstanding"),
				read("outstanding"),
				read("outstanding_note"),
				sub=read("sanctioned_line"),
				icon_name="database",
				script=f"open('{ACCOUNTS_ROUTE}')",
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
		visible="{{ overview.data.tasks && overview.data.tasks.length > 0 }}",
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
				card("Application status", read("applications_note"), applications(read)),
				card(
					"Activity timeline",
					read("activity_note"),
					activity(),
					visible="{{ overview.data.activity && overview.data.activity.length > 0 }}",
				),
			],
			[
				card(
					"Scheduled repayments",
					read("schedule_note"),
					schedule(),
					visible="{{ overview.data.schedule && overview.data.schedule.length > 0 }}",
				)
			],
		),
	]


def build():
	return upsert_page(
		TITLE,
		ROUTE,
		frame(SOURCE, content(), action_label="View payment details", action_route=ACCOUNTS_ROUTE),
		resources=[
			api_resource(SOURCE, "lending.portal.core.get_dashboard"),
			api_resource("alerts", "lending.portal.notifications.get_notifications", auto=0),
		],
	)
