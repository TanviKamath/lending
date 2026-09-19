# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Search page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.search_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.

The box is an ordinary GET form pointed at this same route, so a search is a URL the
borrower can bookmark or send on, the back button steps through the searches they made,
and the page needs not one line of JavaScript. The results come back from the data
script like every other list on the portal.
"""

from lending.portal.build.shell import SEARCH_ROUTE, build_page
from lending.portal.build.theme import (
	BTN_STYLES,
	PRIMARY_TEXT_STYLES,
	SEARCH_BOX_STYLES,
	SEARCH_ROW_STYLES,
	SECONDARY_TEXT_STYLES,
	bind,
	block,
	bound,
	card,
	record_table,
)

PAGE_NAME = "Borrower Search"
ROUTE = SEARCH_ROUTE
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal.search.get_search_page"))  # noqa: F821
'''


def search_form():
	"""One box and one button, posting back to this page as a query on the URL."""
	box = block(
		"input",
		styles=SEARCH_BOX_STYLES,
		attributes={
			"type": "search",
			"name": "q",
			"value": "",
			"placeholder": "Search or type a commands",
			"aria-label": "Search",
			# The rail's icon is the only way onto this page, so whoever arrives came
			# here to type.
			"autofocus": "autofocus",
		},
	)
	# The search comes back in the box it was typed into, rather than the page
	# answering a question it no longer shows.
	bind(box, "query", property="value", type="attribute")

	return block(
		"form",
		styles=SEARCH_ROW_STYLES,
		attributes={"method": "get", "action": f"/{ROUTE}", "role": "search"},
		children=[
			box,
			block("button", styles=BTN_STYLES, html="Search", attributes={"type": "submit"}),
		],
	)


def results():
	"""Every hit is a link, because finding a thing is only half of looking for it."""
	return record_table(
		["Result", "Kind"],
		[
			[
				bound("div", "title", styles=PRIMARY_TEXT_STYLES),
				bound("div", "note", styles=SECONDARY_TEXT_STYLES),
			],
			[bound("div", "kind", styles=SECONDARY_TEXT_STYLES)],
		],
		"results",
	)


def content():
	return [
		card("Search", "results_note", block("div", children=[search_form(), results()])),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Search",
		content(),
		action_href="/borrower/overview",
		data_script=DATA_SCRIPT,
	)
