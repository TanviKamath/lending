# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The portal's frame: the sidebar, the page header, the notifications and the footer.

The Builder shell is one component wrapped *around* each page's content: Builder
merges a component into a page through extend_block, so a page can mirror the frame's
tree and drop its own blocks into the well in the middle.

Studio has no such merge. `StudioComponentWrapper` renders the component's own tree and
discards the instance's children, passing only its props, which the component reads as
`{{ inputs.<name> }}`. A frame that wraps content is therefore not expressible, so the
frame is the pieces that sit *beside* the content -- the sidebar down the left, the
header above, the footer below -- and `frame()` assembles them around whatever a page
passes in.

Three of those are Studio Components, so one edit reaches every page. The sidebar is
not: it is frappe-ui's Sidebar placed straight into each page, because a component's
tree cannot be opened on the canvas and a Sidebar buried in one would be a black box.
See `sidebar`.

The notifications panel is a Dialog rather than the Builder panel, and it reads the
page's own `alerts` data source: a component has no data source of its own, and every
authenticated page carries one under that name for this reason.
"""

from lending.portal.studio_build.app import upsert_component
from lending.portal.studio_build.blocks import (
	badge,
	block,
	button,
	click,
	column,
	container,
	instance,
	muted,
	repeater,
	root,
	row,
	slot,
	spacer,
	text,
)

HEADER = "borrower_header"
FOOTER = "borrower_footer"
ALERTS = "borrower_alerts"

# The rows of the sidebar, and the routes this app serves them at.
#
# lending.hooks.portal_menu_items is the Builder portal's source for these, read back
# per request so a renamed row needs no rebuild. It cannot be that here: its routes are
# the Builder ones (/borrower/loans), the menu is marked current from the request path,
# and a Studio page's request is an API call rather than the page itself. So the rows
# are declared once, here, and a page added is a line here plus a rebuild.
NAV_ITEMS = (
	("Account overview", "/overview", "layout-dashboard"),
	("Loan accounts", "/loans", "wallet"),
	("Applications", "/applications", "file-text"),
	("Documents", "/documents", "paperclip"),
	("Statement of account", "/statement", "receipt"),
	("Interest certificate", "/certificate", "award"),
	("Personal details", "/profile", "user"),
	("Search", "/search", "search"),
)


def sidebar(data):
	"""The list of pages, and whose portal it is.

	frappe-ui's Sidebar itself, sat in the page rather than wrapped in a Studio
	Component of ours. A component renders its own tree and the canvas will not open
	it, so a Sidebar inside one is a black box: its rows, its header and its footer
	slot are all out of reach of the properties panel. Placed directly, every one of
	them is editable where it is drawn.

	What that costs is the copy. The Sidebar is now in all ten authenticated pages
	rather than in one document, so a row added by hand reaches one page -- the rest
	come from a rebuild. The header, the notifications and the footer stay components,
	because nothing in them is worth editing on a page-by-page basis.
	"""
	sections = [
		{
			"label": "",
			"items": [
				{"label": title, "icon": "{{ getIcon('%s') }}" % icon, "to": route}
				for title, route, icon in NAV_ITEMS
			],
		}
	]
	foot = column(
		[
			text("{{ %s.holder_name }}" % data, size="text-sm", styles={"fontWeight": "600"}),
			muted("{{ %s.customer_note }}" % data),
		],
		gap="2px",
		styles={"padding": "12px"},
	)

	return block(
		"Sidebar",
		props={"header": {"title": "{{ %s.brand_name }}" % data}, "sections": sections},
		slots=slot("footer-items", [foot]),
		mobile={"display": "none"},
	)


def header_tree():
	"""The crumb, the day it is being read, and the one thing the page offers to press.

	Every value arrives as an input, so one header serves ten pages. The action hides
	itself where a page passes no label -- the statement and the certificate keep their
	download inside the page, beside the dates it obeys.
	"""
	titles = column(
		[
			text("{{ inputs.crumb }}", tag="h1", size="text-xl", styles={"fontWeight": "600"}),
			muted("{{ inputs.note }}"),
		],
		gap="2px",
	)
	status = badge(
		"{{ inputs.status }}",
		theme="{{ tone(inputs.status_tone) }}",
		visible="{{ inputs.status }}",
	)
	bell = button(
		"",
		script="showAlerts.value = true; alerts.reload()",
		variant="ghost",
		props={"icon": "lucide-bell", "label": "Notifications"},
	)
	action = button(
		"{{ inputs.action_label }}",
		script="open(inputs.action_route)",
		variant="solid",
		visible="{{ inputs.action_label }}",
	)

	return row(
		[titles, spacer(), status, bell, action],
		gap="10px",
		styles={
			"padding": "16px 20px",
			"width": "100%",
			"borderWidth": "0px 0px 1px 0px",
			"borderStyle": "solid",
			"borderColor": "var(--outline-gray-2)",
		},
	)


def alerts_tree():
	"""What is waiting on the borrower and what has happened, over one list of rows.

	The two lists come back in the same {title, note, when, url} shape, so the tab
	switches which array the repeater reads rather than which blocks it draws.
	"""
	alert_row = row(
		[
			column(
				[
					text("{{ dataItem.title }}", size="text-base"),
					muted("{{ dataItem.note }}"),
				],
				gap="2px",
			),
			spacer(),
			muted("{{ dataItem.when }}"),
		],
		gap="10px",
		styles={"padding": "10px 0", "cursor": "pointer"},
		events=click("open(dataItem.url); showAlerts.value = false"),
	)
	tabs = block(
		"TabButtons",
		props={
			"options": [
				{"label": "Notifications", "value": "attention"},
				{"label": "Activity", "value": "activity"},
			],
			"modelValue": {"$type": "variable", "name": "alertsTab"},
			"size": "sm",
		},
	)
	body = column(
		[
			tabs,
			muted("{{ alertsTab === 'attention' ? alerts.data.attention_note : alerts.data.activity_note }}"),
			repeater(
				"{{ alertsTab === 'attention' ? alerts.data.attention : alerts.data.activity }}",
				alert_row,
				empty="Nothing to read",
			),
			button(
				"Mark all as read",
				script="call('lending.portal.notifications.mark_all_as_read').then(() => alerts.reload())",
			),
		],
		gap="10px",
	)

	return block(
		"Dialog",
		props={
			"modelValue": {"$type": "variable", "name": "showAlerts"},
			"title": "Notifications",
			"size": "md",
		},
		children=[body],
	)


def footer_tree():
	"""Whose portal this is, and the policies. Both are Lending Settings, read per request."""
	link = button(
		"{{ dataItem.label }}",
		script="window.location.href = dataItem.href",
		variant="ghost",
		props={"size": "sm"},
	)

	return row(
		[
			muted("{{ inputs.note }}"),
			spacer(),
			repeater("{{ inputs.links }}", link, data_key="label", styles={"display": "flex", "gap": "4px"}),
		],
		gap="10px",
		styles={
			"padding": "12px 20px",
			"width": "100%",
			"borderWidth": "1px 0px 0px 0px",
			"borderStyle": "solid",
			"borderColor": "var(--outline-gray-2)",
		},
	)


def upsert_frame():
	"""Create or replace the three shared components. Safe to re-run.

	The sidebar is not one of them; see `sidebar` for why it is built into each page.
	"""
	upsert_component(
		HEADER,
		"Borrower Page Header",
		header_tree(),
		inputs=(
			("crumb", "What this page is"),
			("note", "Who is reading it, and as on when"),
			("status", "How the borrower's accounts stand, where that is worth saying"),
			("status_tone", "'', 'ok', 'warn' or 'danger'"),
			("action_label", "The one thing the page offers to press; empty hides it"),
			("action_route", "Where that button goes, as a data-layer URL"),
		),
	)
	upsert_component(ALERTS, "Borrower Notifications", alerts_tree())
	upsert_component(
		FOOTER,
		"Borrower Footer",
		footer_tree(),
		inputs=(
			("note", "The lender's copyright line"),
			("links", "The policy links, as {label, href} rows"),
		),
	)


def frame(source, content, action_label="", action_route=""):
	"""One page: the frame, wrapped around this page's own blocks.

	`source` is the name of the page's data source, because every endpoint answers with
	the same frame payload -- the crumb, the holder, the footer -- alongside whatever
	the page itself asked for.
	"""
	data = f"{source}.data"
	header = instance(
		HEADER,
		{
			"crumb": "{{ %s.crumb }}" % data,
			"note": "{{ %s.head_note }}" % data,
			"status": "{{ %s.account_status }}" % data,
			"status_tone": "{{ %s.account_tone }}" % data,
			"action_label": action_label,
			"action_route": action_route,
		},
	)
	footer = instance(
		FOOTER,
		{"note": "{{ %s.copyright_note }}" % data, "links": "{{ %s.footer_links }}" % data},
	)
	body = container(
		content,
		styles={
			"display": "flex",
			"flexDirection": "column",
			"gap": "16px",
			"padding": "20px",
			"width": "100%",
			"flex": "1",
		},
	)
	main = container(
		[header, body, footer, instance(ALERTS)],
		styles={
			"display": "flex",
			"flexDirection": "column",
			"flex": "1",
			"minWidth": "0px",
			"height": "100%",
			"overflowY": "auto",
		},
	)
	return root([sidebar(data), main])
