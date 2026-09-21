# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower portal's frame, stored once as a Builder Component.

Every portal page draws the same rail, sidebar, page head and footer. Copied into each
page, one nav link would need fixing in ten places; held in a Builder Component, an edit
on the canvas propagates to every page that references it.

A page does not simply point at the component. Builder merges a component into a page
through extend_block, which rebuilds the child list from the *page's* children only --
so a page whose reference block has no children renders an empty component. The page
therefore has to mirror the component's tree, one stub per node, each carrying the
referenceBlockId of the node it stands for. reference() below builds that mirror, and
block_id() keeps both sides addressable by path rather than by chance.

The mirror is also where a page differs from the frame: extend_block layers the page
stub's own baseStyles and attributes over the component's, so a page points the header
button wherever it likes without forking the shell.

The sidebar is not one of those differences. It used to be -- each page's mirror froze
its own copy of the menu and marked one row active -- so seven links lived in eleven
stored trees and a renamed route meant rebuilding all of them. The menu now comes from
lending.hooks.portal_menu_items through Frappe's portal menu, read per request, and the
frame holds a single row block repeated over it.
"""

import json

import frappe

from lending.portal.build.script import CLIENT_SCRIPT, SCRIPT_NAME
from lending.portal.build.theme import (
	ALERTS_ACTION_STYLES,
	ALERTS_AVATAR_STYLES,
	ALERTS_BODY_STYLES,
	ALERTS_DOT_STYLES,
	ALERTS_HEAD_STYLES,
	ALERTS_NOTE_STYLES,
	ALERTS_ROW_BODY_STYLES,
	ALERTS_ROW_NOTE_STYLES,
	ALERTS_ROW_STYLES,
	ALERTS_ROW_TITLE_STYLES,
	ALERTS_ROW_WHEN_STYLES,
	ALERTS_STYLES,
	ALERTS_TAB_STYLES,
	AVATAR_STYLES,
	BODY_STYLES,
	BTN_STYLES,
	CHEVRON_LEFT,
	CONTENT_STYLES,
	CRUMB_STYLES,
	DIALOG_BODY_STYLES,
	DIALOG_FOOT_STYLES,
	DIALOG_HEAD_STYLES,
	DIALOG_INPUT_STYLES,
	DIALOG_NOTE_STYLES,
	DIALOG_ROW_KIND_STYLES,
	DIALOG_ROW_STYLES,
	DIALOG_ROW_TITLE_STYLES,
	DIALOG_STYLES,
	FOOTER_LINK_STYLES,
	FOOTER_LINKS_STYLES,
	FOOTER_NOTE_STYLES,
	FOOTER_STYLES,
	HEAD_END_STYLES,
	HEAD_HTML,
	HEAD_NOTE_STYLES,
	HIDDEN,
	HINT_STYLES,
	ICON_BELL,
	ICON_BRAND,
	ICON_CHECK_CHECK,
	ICON_CLOSE,
	ICON_SEARCH,
	KEY_STYLES,
	MAIN_STYLES,
	MARK_STYLES,
	NAV_ITEM_STYLES,
	NAV_STYLES,
	OVERLAY_STYLES,
	PAGE_HEAD_STYLES,
	RAIL_DIVIDER_STYLES,
	RAIL_ICON_STYLES,
	RAIL_STYLES,
	SHELL_STATE_CSS,
	SHELL_STYLES,
	SIDE_BRAND_STYLES,
	SIDE_COLLAPSE_STYLES,
	SIDE_FOOT_NAME_STYLES,
	SIDE_FOOT_NOTE_STYLES,
	SIDE_FOOT_STYLES,
	SIDE_HEAD_STYLES,
	SIDE_LOGO_STYLES,
	SIDEBAR_STYLES,
	SPACER_STYLES,
	badge,
	bind,
	block,
	block_id,
	bound,
	brand_lockup,
	empty_block_fields,
	repeater,
	upsert_tokens,
)

# Builder Component autonames by field:component_id, so this is the document name too.
# A fixed slug keeps every site addressing the same component.
COMPONENT_ID = "lending-borrower-shell"
COMPONENT_NAME = "Borrower Portal Shell"

# The one page the rail opens. It is not a sidebar row -- the rail is its way in -- so
# it is not in lending.hooks.portal_menu_items, and the route is spelt here rather than
# in the module that builds the page: the rail needs it too, and that module already
# imports build_page from this one.
#
# The bell used to have a page of the same kind at borrower/notifications. It said the
# same thing the panel says, so pressing the bell left a borrower with two places to
# read one list, and the page is gone: the panel is the whole of the notifications.
SEARCH_ROUTE = "borrower/search"

# Paths a page overrides through its mirror. Named here so a page never types a path.
CONTENT_PATH = "shell/main/content"
ACTION_PATH = "shell/main/head/end/action"


def rail():
	return block(
		"div",
		path="shell/rail",
		styles=RAIL_STYLES,
		mobileStyles=HIDDEN,
		children=[
			block("span", path="shell/rail/mark", styles=MARK_STYLES, html=ICON_BRAND),
			block("span", path="shell/rail/divider", styles=RAIL_DIVIDER_STYLES),
			block(
				"a",
				path="shell/rail/search",
				styles=RAIL_ICON_STYLES,
				html=ICON_SEARCH,
				# The href is the page, and the script takes the click to open the dialog
				# over whatever the borrower is already reading. Where no script runs,
				# the link is what happens.
				attributes={
					"href": f"/{SEARCH_ROUTE}",
					"aria-label": "Search",
					"data-search-open": "1",
				},
			),
			block(
				"button",
				path="shell/rail/alerts",
				styles=RAIL_ICON_STYLES,
				html=ICON_BELL,
				# A button and not a link, unlike the magnifier beside it. The magnifier
				# has a page to fall back to where no script runs; the bell has nothing
				# behind it but the panel, so a link would be an invitation to a route
				# that does not exist.
				#
				# It is also a toggle: the panel sits beside the sidebar rather than
				# over the page, so the button stays in view and has to say whether it
				# is on. The script keeps aria-expanded true while the panel is out, and
				# SHELL_STATE_CSS draws that as the pressed state the desk's dock gives
				# its own selected item.
				attributes={
					"type": "button",
					"aria-label": "Notifications",
					"data-alerts-open": "1",
					"aria-expanded": "false",
				},
			),
			block("span", path="shell/rail/spacer", styles=SPACER_STYLES),
			bound("span", "initials", path="shell/rail/avatar", styles=AVATAR_STYLES),
		],
	)


def collapse_toggle():
	"""The control that gets the sidebar out of the way, and brings it back.

	One button for both directions: the script turns it over, so there is never a
	moment where the menu is shut and nothing on screen will reopen it.
	"""
	return block(
		"button",
		path="shell/sidebar/collapse",
		styles=SIDE_COLLAPSE_STYLES,
		html=CHEVRON_LEFT,
		attributes={
			"type": "button",
			"data-sidebar-toggle": "1",
			"aria-label": "Hide the menu",
			"aria-expanded": "true",
		},
	)


def nav():
	"""The menu, as one row rendered once per row of the portal menu.

	The rows are not written here. lending.hooks.portal_menu_items declares them and
	portal.core.nav_items reads them back through Frappe's own portal menu, so the
	sidebar is whatever the site's menu says it is at the moment the page is served:
	a row renamed, reordered or switched off needs no rebuild of anything.

	aria-current is the row's own answer to which page it is on. The data script sets
	it to "page" on one row, which both tells a screen reader where it is and is what
	SHELL_STATE_CSS marks the row with.
	"""
	row = block(
		"a",
		path="shell/sidebar/nav/row",
		styles=NAV_ITEM_STYLES,
		attributes={"href": "#", "aria-current": "false"},
	)
	bind(row, "nav_title")
	bind(row, "nav_route", property="href", type="attribute")
	bind(row, "nav_current", property="aria-current", type="attribute")

	return repeater(
		"nav_items",
		row,
		element="nav",
		path="shell/sidebar/nav",
		styles=NAV_STYLES,
		attributes={"data-portal-nav": "1"},
	)


def sidebar():
	"""The list of pages, whose portal it is, and the toggle that gets it out of the way.

	It used to open with a record switcher, reading "All customer records" and how many
	there were. The count is at the foot already, under the name of whoever is signed
	in, which is where it means something, and a switcher between one thing read as a
	control that does nothing.
	"""
	return block(
		"aside",
		path="shell/sidebar",
		styles=SIDEBAR_STYLES,
		mobileStyles=HIDDEN,
		attributes={"data-sidebar": "1"},
		children=[
			block(
				"div",
				path="shell/sidebar/brand",
				styles=SIDE_BRAND_STYLES,
				children=brand_lockup(
					SIDE_HEAD_STYLES, logo_styles=SIDE_LOGO_STYLES, path="shell/sidebar/brand"
				),
			),
			collapse_toggle(),
			nav(),
			block(
				"div",
				path="shell/sidebar/foot",
				styles=SIDE_FOOT_STYLES,
				children=[
					bound(
						"b", "holder_name", path="shell/sidebar/foot/name", styles=SIDE_FOOT_NAME_STYLES
					),
					bound(
						"span",
						"customer_note",
						path="shell/sidebar/foot/note",
						styles=SIDE_FOOT_NOTE_STYLES,
					),
				],
			),
		],
	)


# What the dialog's foot says it can do, in the desk's own words and its own grouping:
# the keys for one action sit together, and the phrase follows them. Up and down are
# two keys and get two caps, because that is what a hand does with them.
SEARCH_KEYS = (
	(("↑", "↓"), "to navigate"),
	(("↵",), "to select"),
	(("Esc",), "to close"),
)


def search_dialog():
	"""The command box the rail's magnifier opens, over whatever page is underneath.

	One row is written here and the client script clones it per result, which is how
	the rest of the portal renders a list it did not know the length of at build time
	-- see script.fillOffer. So every style stays in theme and the script only ever
	sets text.
	"""
	row = block(
		"a",
		path="shell/search/row",
		styles=DIALOG_ROW_STYLES,
		attributes={"href": "#", "data-search-row": "1", "hidden": "hidden"},
		children=[
			block(
				"span",
				path="shell/search/row/title",
				styles=DIALOG_ROW_TITLE_STYLES,
				attributes={"data-row-title": "1"},
			),
			block(
				"span",
				path="shell/search/row/kind",
				styles=DIALOG_ROW_KIND_STYLES,
				attributes={"data-row-kind": "1"},
			),
		],
	)

	hints = [
		block(
			"span",
			path=f"shell/search/hint/{index}",
			styles=HINT_STYLES,
			children=[
				*(
					block(
						"span",
						path=f"shell/search/hint/{index}/key/{position}",
						styles=KEY_STYLES,
						html=key,
					)
					for position, key in enumerate(keys)
				),
				block("span", path=f"shell/search/hint/{index}/label", html=label),
			],
		)
		for index, (keys, label) in enumerate(SEARCH_KEYS)
	]

	return block(
		"div",
		path="shell/search",
		styles=OVERLAY_STYLES,
		attributes={"data-search-overlay": "1", "hidden": "hidden"},
		children=[
			block(
				"div",
				path="shell/search/dialog",
				styles=DIALOG_STYLES,
				attributes={"role": "dialog", "aria-label": "Search"},
				children=[
					block(
						"div",
						path="shell/search/head",
						styles=DIALOG_HEAD_STYLES,
						children=[
							block("span", path="shell/search/head/icon", html=ICON_SEARCH),
							block(
								"input",
								path="shell/search/head/input",
								styles=DIALOG_INPUT_STYLES,
								attributes={
									"type": "search",
									"data-search-input": "1",
									"placeholder": "Search or type a command",
									# Not "Search" again: the dialog around it is already
									# announced by that name, and a reader that says it
									# twice has told you nothing the second time.
									"aria-label": "What are you looking for",
								},
							),
						],
					),
					block(
						"div",
						path="shell/search/results",
						styles=DIALOG_BODY_STYLES,
						attributes={"data-search-results": "1"},
						children=[row],
					),
					# Only ever shown when the list is empty, which is a search that
					# matched nothing: the script puts the server's wording here and
					# hides it again the moment there is a row to read instead.
					block(
						"div",
						path="shell/search/note",
						styles=DIALOG_NOTE_STYLES,
						attributes={"data-search-note": "1"},
						html="Type to search your loan accounts, applications and documents",
					),
					block("div", path="shell/search/foot", styles=DIALOG_FOOT_STYLES, children=hints),
				],
			)
		],
	)


def alerts_panel():
	"""The panel the rail's bell drops down, beside the sidebar.

	Two tabs over one list of rows, because the rows are one shape: the data layer
	hands back what is waiting and what has happened in the same {title, note, when,
	url} form, so switching tab re-renders the same block rather than a second one.
	"""
	tabs = [
		block(
			"button",
			path=f"shell/alerts/tab/{name}",
			styles=ALERTS_TAB_STYLES,
			html=label,
			attributes={
				"type": "button",
				"data-alerts-tab": name,
				"aria-selected": "true" if name == "attention" else "false",
			},
		)
		for name, label in (("attention", "Notifications"), ("activity", "Activity"))
	]

	row = block(
		"a",
		path="shell/alerts/row",
		styles=ALERTS_ROW_STYLES,
		attributes={"href": "#", "data-alerts-row": "1", "hidden": "hidden"},
		children=[
			block(
				"span",
				path="shell/alerts/row/dot",
				styles=ALERTS_DOT_STYLES,
				attributes={"data-row-dot": "1"},
			),
			block(
				"span",
				path="shell/alerts/row/mark",
				styles=ALERTS_AVATAR_STYLES,
				attributes={"data-row-mark": "1"},
			),
			block(
				"span",
				path="shell/alerts/row/body",
				styles=ALERTS_ROW_BODY_STYLES,
				children=[
					block(
						"span",
						path="shell/alerts/row/title",
						styles=ALERTS_ROW_TITLE_STYLES,
						attributes={"data-row-title": "1"},
					),
					block(
						"span",
						path="shell/alerts/row/note",
						styles=ALERTS_ROW_NOTE_STYLES,
						attributes={"data-row-note": "1"},
					),
					block(
						"span",
						path="shell/alerts/row/when",
						styles=ALERTS_ROW_WHEN_STYLES,
						attributes={"data-row-when": "1"},
					),
				],
			),
		],
	)

	return block(
		"aside",
		path="shell/alerts",
		styles=ALERTS_STYLES,
		attributes={"data-alerts-panel": "1", "hidden": "hidden"},
		children=[
			block(
				"div",
				path="shell/alerts/head",
				styles=ALERTS_HEAD_STYLES,
				children=[
					*tabs,
					block("span", path="shell/alerts/head/spacer", styles=SPACER_STYLES),
					block(
						"button",
						path="shell/alerts/head/read",
						styles=ALERTS_ACTION_STYLES,
						html=ICON_CHECK_CHECK,
						attributes={
							"type": "button",
							"data-alerts-read": "1",
							"aria-label": "Mark all as read",
							"title": "Mark all as read",
						},
					),
					block(
						"button",
						path="shell/alerts/head/close",
						styles=ALERTS_ACTION_STYLES,
						html=ICON_CLOSE,
						attributes={"type": "button", "data-alerts-close": "1", "aria-label": "Close"},
					),
				],
			),
			block(
				"div",
				path="shell/alerts/body",
				styles=ALERTS_BODY_STYLES,
				attributes={"data-alerts-body": "1"},
				children=[row],
			),
			block(
				"div",
				path="shell/alerts/note",
				styles=ALERTS_NOTE_STYLES,
				attributes={"data-alerts-note": "1"},
				html="Reading your account…",
			),
		],
	)


def crest():
	"""How the borrower's accounts stand, when that is worth a line of its own.

	It hides on an empty account_status rather than rendering an empty pill. That is
	how core.account_status declines to repeat a single account's own badge back at
	it: the head reports standing the page's rows cannot, and says nothing when they
	already have.
	"""
	node = badge("account_status", tone_key="account_tone", path="shell/main/head/end/status")
	node["visibilityCondition"] = "account_status"

	return node


def page_head():
	"""The crumb, the note and the button label all arrive from the page's data script.

	Each page supplies its own crumb and action_label, so one frame serves them all.
	The button's href is a per-page attribute override -- see reference().
	"""
	return block(
		"div",
		path="shell/main/head",
		styles=PAGE_HEAD_STYLES,
		children=[
			bound("span", "crumb", path="shell/main/head/crumb", styles=CRUMB_STYLES),
			bound("span", "head_note", path="shell/main/head/note", styles=HEAD_NOTE_STYLES),
			block(
				"div",
				path="shell/main/head/end",
				styles=HEAD_END_STYLES,
				children=[
					crest(),
					bound(
						"a",
						"action_label",
						path=ACTION_PATH,
						styles=BTN_STYLES,
						attributes={"href": "#"},
					),
				],
			),
		],
	)


def footer():
	"""Whose portal this is, the policies, and how to complain about it.

	Nothing here names Frappe, and nothing here is written by us. The notice on the
	left and the links on the right are both Lending Settings, so the foot of the page
	says what a regulator expects this lender to say.

	The links are a repeater over portal.core.footer_links rather than a block each,
	which is what makes them a setting at all: a lender adding a policy changes a row
	in a child table and the next page served has it. Written as blocks, the count
	would be frozen at build time and every change would mean rebuilding ten pages --
	the same reason the sidebar stopped being blocks. See nav() above.
	"""
	link = block(
		"a",
		path="shell/main/footer/links/row",
		styles=FOOTER_LINK_STYLES,
		attributes={"href": "#"},
	)
	bind(link, "footer_label")
	bind(link, "footer_href", property="href", type="attribute")

	return block(
		"footer",
		path="shell/main/footer",
		styles=FOOTER_STYLES,
		children=[
			bound(
				"span",
				"copyright_note",
				path="shell/main/footer/note",
				styles=FOOTER_NOTE_STYLES,
			),
			repeater(
				"footer_links",
				link,
				element="nav",
				path="shell/main/footer/links",
				styles=FOOTER_LINKS_STYLES,
				attributes={"data-footer-links": "1", "aria-label": "Policies"},
			),
		],
	)


def tree():
	"""The component's own block, the frame with an empty content well in the middle."""
	return block(
		"div",
		path="shell",
		styles=SHELL_STYLES,
		children=[
			rail(),
			sidebar(),
			# After the sidebar and before the main column: the panel is fixed, so it
			# takes no width here, but SHELL_STATE_CSS finds it as the sidebar's own
			# sibling to decide which side it is fixed to.
			alerts_panel(),
			block(
				"div",
				path="shell/main",
				styles=MAIN_STYLES,
				children=[
					page_head(),
					block("main", path=CONTENT_PATH, styles=CONTENT_STYLES),
					footer(),
				],
			),
			search_dialog(),
		],
	)


def stub(node, overrides):
	"""Mirror one component node as the page-side block that stands in for it.

	The stub carries no styling of its own -- Builder resolves that from the component
	at render time -- except where overrides name this node's path.
	"""
	path = node["path"]
	override = overrides.get(path) or {}

	mirror = {
		"blockId": block_id(f"ref/{path}"),
		"referenceBlockId": node["blockId"],
		# The component id, not the readable name: the canvas looks a stub's component up
		# in its store by this exact value (block.ts referenceComponent), the same key
		# extendedFromComponent uses. The readable name here leaves every stub unresolved,
		# so the shell renders on the published page and stays invisible on the canvas.
		"isChildOfComponent": COMPONENT_ID,
		**empty_block_fields(),
		"baseStyles": dict(override.get("baseStyles") or {}),
		"attributes": dict(override.get("attributes") or {}),
		"children": [stub(child, overrides) for child in node.get("children") or []],
	}

	# Children the component has no counterpart for are appended as they are, which is
	# how a page drops its own content into the frame's content well.
	mirror["children"].extend(override.get("extra_children") or [])

	return mirror


def reference(content, action_href="#"):
	"""The page-side block that renders the shell with this page's content inside it.

	`content` is the page's own blocks and `action_href` is where the header button
	points, or None on a page that wants no header button at all. Which nav row is lit
	is not a page's business any more: the row knows, from the route being served.
	"""
	overrides = {
		CONTENT_PATH: {"extra_children": content},
		# The button is the frame's, so a page that has no use for it hides its own stub
		# rather than forking the shell.
		ACTION_PATH: (
			{"attributes": {"href": action_href}} if action_href else {"baseStyles": {"display": "none"}}
		),
	}

	mirror = stub(tree(), overrides)
	mirror["extendedFromComponent"] = COMPONENT_ID

	return mirror


def strip_paths(node):
	"""Drop the authoring-only path key before the tree is stored."""
	node.pop("path", None)
	for child in node.get("children") or []:
		strip_paths(child)

	return node


def upsert_component():
	"""Create or replace the shell component. Safe to re-run: block ids are by path."""
	fields = {
		"component_name": COMPONENT_NAME,
		"component_id": COMPONENT_ID,
		"block": json.dumps(strip_paths(tree()), indent=1),
	}

	if frappe.db.exists("Builder Component", COMPONENT_ID):
		doc = frappe.get_doc("Builder Component", COMPONENT_ID)
		# Saving a component queues a cache-clear job and locks the document, so
		# building several pages in a row would collide on it. The shell is identical
		# for every page, so an unchanged block is left alone.
		if doc.block == fields["block"] and doc.component_name == fields["component_name"]:
			return doc.name, "unchanged"

		doc.update(fields)
		doc.save()
		action = "updated"
	else:
		doc = frappe.get_doc(dict(doctype="Builder Component", **fields)).insert()
		action = "created"

	return doc.name, action


def upsert_client_script(script_name, script):
	"""Create or replace a JavaScript Builder Client Script, returning its document name.

	Builder writes the script to a public file and serves it from the published page,
	which is how a page gets behaviour without the editor's own bundle.
	"""
	existing = frappe.db.get_value("Builder Client Script", {"name": script_name}, "name")
	if existing:
		doc = frappe.get_doc("Builder Client Script", existing)
		if doc.script == script:
			return doc.name
		doc.script = script
		doc.save()
		return doc.name

	doc = frappe.get_doc(
		{
			"doctype": "Builder Client Script",
			"name": script_name,
			"script_type": "JavaScript",
			"script": script,
		}
	).insert()

	return doc.name


def build_page(
	page_name,
	route,
	title,
	content,
	action_href="#",
	data_script=None,
	authenticated=True,
	extra_css="",
):
	"""Create or replace one portal page: the shared shell, wrapped around `content`.

	Every page is assembled the same way, so the only per-page arguments are its route,
	where its header button goes -- None for no button -- and its data script.

	`extra_css` is for a rule one page needs and the others do not, typically because
	that page repeats a block and so cannot style each copy. It goes in the page's own
	head rather than in SHELL_STATE_CSS, which every page carries a copy of: a rule
	added there is only served after all eleven have been rebuilt.

	It is appended to the head as it stands, so it carries its own `<style>` tags. Bare
	rules land after the shell's closing tag and the browser prints them on the page.
	"""
	upsert_tokens()
	component, component_action = upsert_component()

	# A public page cannot wear the borrower frame: every row in that sidebar needs a
	# login, so a guest clicking one would be bounced. Public pages get their content
	# straight in the body and carry their own heading.
	children = [reference(content, action_href)] if authenticated else list(content)
	body = block("div", styles=BODY_STYLES, originalElement="body", children=children)

	fields = {
		"page_name": page_name,
		"page_title": title,
		"route": route,
		"published": 1,
		"authenticated_access": 1 if authenticated else 0,
		"disable_indexing": 1,
		"is_standard": 1,
		"app": "lending",
		"head_html": HEAD_HTML + SHELL_STATE_CSS + extra_css,
		"page_data_script": data_script or "",
		"blocks": frappe.as_json([body]),
		# A leftover draft outranks what this script just wrote: the canvas loads
		# draft_blocks when it exists, and export_page_as_standard prefers it over
		# blocks. Left in place, a rebuild reaches the published route and nowhere else.
		"draft_blocks": None,
	}

	# Every page gets the one shared script, not just the pages with a form: the shell
	# itself has behaviour now, since the sidebar remembers whether it is open.
	fields["client_scripts"] = [{"builder_script": upsert_client_script(SCRIPT_NAME, CLIENT_SCRIPT)}]

	existing = frappe.db.get_value("Builder Page", {"route": route}, "name")
	if existing:
		page = frappe.get_doc("Builder Page", existing)
		page.update(fields)
		page.save()
		action = "updated"
	else:
		page = frappe.get_doc(dict(doctype="Builder Page", **fields)).insert()
		action = "created"

	# The save alone does not always reach the process that serves the page: a stale
	# document_cache entry in Redis outlived a rebuild, a cache clear and a restart, and
	# the browser kept getting the previous build. Dropping it by name here is what makes
	# a rebuild something you can see.
	frappe.clear_document_cache("Builder Page", page.name)
	frappe.db.commit()
	print(f"{component_action} Builder Component {component}")
	print(f"{action} Builder Page {page.name} at /{route}")

	return page.name
