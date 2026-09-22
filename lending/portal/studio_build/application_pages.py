# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower's Applications list, and one application's tracker.

Both replace pages of the Builder portal this one was migrated from, and read the
same two endpoints it read.

The tracker leads on the detail page, because "where has my application got to" is the
question that brings a borrower here. Under it, what they asked for: four sets of
label-and-value pairs, which the Builder page stacked behind a tab strip built out of
buttons and a stylesheet, and this one hands to frappe-ui's TabButtons.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	block,
	breadcrumb_trail,
	card,
	column,
	muted,
	pair_grid,
	pair_rows,
	reader,
	record_list,
	repeater,
	row,
	spacer,
	text,
	toned_badge,
)
from lending.portal.studio_build.shell import frame

LIST_SOURCE = "applications"
DETAIL_SOURCE = "application"
ALERTS = ("alerts", "lending.portal.notifications.get_notifications")

# What the preview holds, in the order a borrower checks it: the loan first, because
# that is what the application is, then who it is for, then what went with it.
SECTIONS = (
	("Loan details", "terms", False),
	("Your details", "applicant", False),
	("Co-applicants", "co_applicants", True),
	("Documents", "documents", True),
)


# --- the list -----------------------------------------------------------------------


def applications(read):
	"""Each row links to its own tracker, so the whole line is the way in."""
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


def list_content(read):
	return [
		card("Applications", read("applications_note"), applications(read)),
		# What a borrower has before any of it becomes an application. On the day they
		# sign up this card is their whole account, so the page cannot leave it out.
		card("Enquiries", read("enquiries_note"), pair_rows(read("enquiries"), with_detail=True)),
	]


def build_list():
	read = reader(LIST_SOURCE)

	return upsert_page(
		"Applications",
		"/applications",
		frame(
			LIST_SOURCE,
			list_content(read),
			action_label="Apply for a loan",
			action_route="/apply",
		),
		[
			api_resource(LIST_SOURCE, "lending.portal.applications.get_applications_page"),
			api_resource(*ALERTS, auto=0),
		],
	)


# --- one application ------------------------------------------------------------------


def tracker(read):
	"""How far the file has got, as a step per stage.

	`mark` is the tick, the ring or the empty dot the data layer decides, and `tone`
	is how loudly it says so -- the same {title, note, mark, tone} rows the public
	tracker at /track draws.
	"""
	step = column(
		[
			row([muted("{{ dataItem.mark }}"), text("{{ dataItem.title }}", size="text-base")], gap="6px"),
			muted("{{ dataItem.note }}"),
		],
		gap="2px",
		styles={"flex": "1", "minWidth": "0px"},
	)

	return repeater(
		read("steps"),
		step,
		data_key="title",
		styles={"display": "flex", "flexDirection": "row", "gap": "12px", "width": "100%"},
		mobile={"flexDirection": "column"},
	)


def lead_card(read):
	"""The product, the reference and where the file stands, above everything else."""
	head = column(
		[
			row(
				[
					text(read("product"), tag="h2", size="text-2xl", styles={"fontWeight": "600"}),
					spacer(),
					muted(read("as_on")),
				],
				gap="10px",
			),
			muted(read("reference")),
		],
		gap="2px",
	)

	return card(
		"",
		"",
		column([head, tracker(read), muted(read("headline")), muted(read("headline_note"))], gap="12px"),
	)


def preview(read):
	"""Four sets of pairs behind four tabs, rather than four screens of scroll.

	TabButtons and a ref, rather than the Tabs component: Tabs renders its panel slot
	once for whichever tab is open and hands the tab to the slot, so four panels in it
	would all draw at once. Which section is showing is this page's own state, so the
	page script holds it and each panel says when it is the one being read.
	"""
	tabs = block(
		"TabButtons",
		props={
			"options": [{"label": label, "value": key} for label, key, _detail in SECTIONS],
			"modelValue": {"$type": "variable", "name": "previewTab"},
			"size": "sm",
		},
	)
	panels = [
		column(
			[muted(read(f"{key}_note")), pair_grid(read(key), with_detail=detail)],
			gap="10px",
			visible="{{ previewTab === '%s' }}" % key,
		)
		for _label, key, detail in SECTIONS
	]

	return column([tabs, *panels], gap="12px")


def detail_content(read):
	breadcrumbs = breadcrumb_trail([
		{"label": "Applications", "route": "/borrower-portal/applications"},
		{"label": read("reference")},
	])
	return [breadcrumbs, lead_card(read), card("Application preview", read("preview_note"), preview(read))]


def build_detail():
	read = reader(DETAIL_SOURCE)

	return upsert_page(
		"Application",
		"/application/:name",
		frame(
			DETAIL_SOURCE,
			detail_content(read),
		),
		[
			api_resource(
				DETAIL_SOURCE,
				"lending.portal.applications.get_application_detail",
				params={"name": "{{ route.params.name }}"},
			),
			api_resource(*ALERTS, auto=0),
		],
		script=page_script(state=[("previewTab", '"terms"')]),
	)


def build():
	return build_list(), build_detail()
