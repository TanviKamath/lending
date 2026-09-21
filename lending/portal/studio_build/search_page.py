# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower's Search page, as a Studio page.

It replaces `portal.build.search_page` and reads `get_search_page`, which answers with
the results and the frame payload together.

The Builder page was a plain GET form pointed at its own route, so a search was a URL
the borrower could bookmark and the page needed no JavaScript. Here the box is a
TextInput over a ref and the data source carries the query as a parameter.

The typing is kept off the wire deliberately. An API Resource re-fetches whenever its
parameters change, and this endpoint answers with the whole frame alongside the results,
so a source bound straight to the box would refetch the sidebar on every keystroke. The
box writes `draft`; pressing Search copies it into `query`, which is what the source
reads.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	block,
	button,
	card,
	column,
	muted,
	reader,
	record_list,
	row,
	text,
)
from lending.portal.studio_build.shell import frame

SOURCE = "search"
read = reader(SOURCE)

SUBMIT = "query.value = draft.value"


def search_box():
	"""One box and one button. Enter does what the button does, because a search is typed."""
	box = block(
		"TextInput",
		props={
			"placeholder": "Search your loan accounts, applications and documents",
			"modelValue": {"$type": "variable", "name": "draft"},
		},
		styles={"flex": "1", "minWidth": "0px"},
		events={
			"keyup.enter": {"event": "keyup.enter", "action": "Run Script", "script": SUBMIT},
		},
	)

	return row([box, button("Search", script=SUBMIT, variant="solid")], gap="8px")


def results():
	"""Every hit is a link, because finding a thing is only half of looking for it."""
	return record_list(
		[("minmax(0, 1fr)", "Result"), ("10rem", "Kind")],
		read("results"),
		[
			[text("{{ item.title }}", size="text-base"), muted("{{ item.note }}")],
			[muted("{{ item.kind }}")],
		],
		row_key="url",
		script="open(item.url)",
	)


def content():
	return [card("Search", read("results_note"), column([search_box(), results()], gap="12px"))]


def build():
	return upsert_page(
		"Search",
		"/search",
		frame(SOURCE, content(), action_label="Account overview", action_route="/borrower/overview"),
		[
			api_resource(SOURCE, "lending.portal.search.get_search_page", params={"q": "{{ query }}"}),
			api_resource("alerts", "lending.portal.notifications.get_notifications", auto=0),
		],
		script=page_script(state=[("draft", '""'), ("query", '""')]),
	)
