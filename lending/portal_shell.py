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
stub's own baseStyles and attributes over the component's, so a page marks its own nav
row active and points the header button wherever it likes, without forking the shell.
"""

import json

import frappe

from lending.portal_theme import (
	AVATAR_STYLES,
	BODY_STYLES,
	BTN_STYLES,
	CONTENT_STYLES,
	CRUMB_STYLES,
	FOOTER_LINK_STYLES,
	FOOTER_STYLES,
	HEAD_END_STYLES,
	HEAD_HTML,
	HEAD_NOTE_STYLES,
	HIDDEN,
	ICON_BELL,
	ICON_BRAND,
	ICON_SEARCH,
	MAIN_STYLES,
	MARK_STYLES,
	NAV_ITEM_ACTIVE_STYLES,
	NAV_ITEM_STYLES,
	NAV_STYLES,
	PAGE_HEAD_STYLES,
	RAIL_DIVIDER_STYLES,
	RAIL_ICON_STYLES,
	RAIL_STYLES,
	SHELL_STYLES,
	SIDE_FOOT_NAME_STYLES,
	SIDE_FOOT_NOTE_STYLES,
	SIDE_FOOT_STYLES,
	SIDE_HEAD_STYLES,
	SIDEBAR_STYLES,
	SPACER_STYLES,
	STATUS_DOT_STYLES,
	STATUS_STYLES,
	SWITCHER_NAME_STYLES,
	SWITCHER_NOTE_STYLES,
	SWITCHER_STYLES,
	block,
	block_id,
	bound,
	empty_block_fields,
	upsert_tokens,
)

# Builder Component autonames by field:component_id, so this is the document name too.
# A fixed slug keeps every site addressing the same component.
COMPONENT_ID = "lending-borrower-shell"
COMPONENT_NAME = "Borrower Portal Shell"

# One row per page the borrower can actually open. PORTAL_PLAN.md section 6.7 keeps
# repayments, disbursements and charges as sections of a loan, not as pages, so the
# sidebar does not offer them.
NAV_LINKS = (
	("Account overview", "/borrower/overview"),
	("Loan accounts", "/borrower/loans"),
	("Applications", "/borrower/applications"),
	("Documents", "/borrower/documents"),
	("Statement of account", "/borrower/statement"),
	("Interest certificate", "/borrower/certificate"),
	("Personal details", "/borrower/profile"),
)

FOOTER_LINKS = ("Fair practice code", "Grievance redressal", "Interest rate policy")

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
				attributes={"href": "#", "aria-label": "Search"},
			),
			block(
				"a",
				path="shell/rail/alerts",
				styles=RAIL_ICON_STYLES,
				html=ICON_BELL,
				attributes={"href": "#", "aria-label": "Notifications"},
			),
			block("span", path="shell/rail/spacer", styles=SPACER_STYLES),
			bound("span", "initials", path="shell/rail/avatar", styles=AVATAR_STYLES),
		],
	)


def sidebar():
	nav_items = [
		block(
			"a",
			path=f"shell/sidebar/nav/{href}",
			styles=NAV_ITEM_STYLES,
			html=label,
			attributes={"href": href},
		)
		for label, href in NAV_LINKS
	]

	return block(
		"aside",
		path="shell/sidebar",
		styles=SIDEBAR_STYLES,
		mobileStyles=HIDDEN,
		children=[
			bound("div", "brand_name", path="shell/sidebar/brand", styles=SIDE_HEAD_STYLES),
			block(
				"div",
				path="shell/sidebar/switcher",
				styles=SWITCHER_STYLES,
				children=[
					block(
						"b",
						path="shell/sidebar/switcher/name",
						styles=SWITCHER_NAME_STYLES,
						html="All customer records",
					),
					bound(
						"span",
						"customer_note",
						path="shell/sidebar/switcher/note",
						styles=SWITCHER_NOTE_STYLES,
					),
				],
			),
			block("nav", path="shell/sidebar/nav", styles=NAV_STYLES, children=nav_items),
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
					block(
						"span",
						path="shell/main/head/end/status",
						styles=STATUS_STYLES,
						children=[
							block("span", path="shell/main/head/end/status/dot", styles=STATUS_DOT_STYLES),
							bound("span", "account_status", path="shell/main/head/end/status/text"),
						],
					),
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
	links = [
		block(
			"a",
			path=f"shell/main/footer/link/{index}",
			styles=FOOTER_LINK_STYLES,
			html=label,
			attributes={"href": "#"},
		)
		for index, label in enumerate(FOOTER_LINKS)
	]

	return block(
		"footer",
		path="shell/main/footer",
		styles=FOOTER_STYLES,
		children=[
			bound("span", "brand_name", path="shell/main/footer/brand"),
			block("span", path="shell/main/footer/links", children=links),
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


def reference(content, active_href, action_href="#"):
	"""The page-side block that renders the shell with this page's content inside it.

	`content` is the page's own blocks, `active_href` the nav row to mark active, and
	`action_href` where the header button points.
	"""
	overrides = {
		CONTENT_PATH: {"extra_children": content},
		ACTION_PATH: {"attributes": {"href": action_href}},
	}
	if active_href:
		overrides[f"shell/sidebar/nav/{active_href}"] = {"baseStyles": NAV_ITEM_ACTIVE_STYLES}

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
		doc.update(fields)
		doc.save()
		action = "updated"
	else:
		doc = frappe.get_doc(dict(doctype="Builder Component", **fields)).insert()
		action = "created"

	return doc.name, action


def build_page(page_name, route, title, nav_href, content, action_href="#", data_script=None):
	"""Create or replace one portal page: the shared shell, wrapped around `content`.

	Every page is assembled the same way, so the only per-page arguments are its route,
	which nav row it lights up, where its header button goes, and its data script.
	"""
	upsert_tokens()
	component, component_action = upsert_component()

	body = block(
		"div",
		styles=BODY_STYLES,
		originalElement="body",
		children=[reference(content, nav_href, action_href)],
	)

	fields = {
		"page_name": page_name,
		"page_title": title,
		"route": route,
		"published": 1,
		"authenticated_access": 1,
		"disable_indexing": 1,
		"is_standard": 1,
		"app": "lending",
		"head_html": HEAD_HTML,
		"page_data_script": data_script or "",
		"blocks": frappe.as_json([body]),
		# A leftover draft outranks what this script just wrote: the canvas loads
		# draft_blocks when it exists, and export_page_as_standard prefers it over
		# blocks. Left in place, a rebuild reaches the published route and nowhere else.
		"draft_blocks": None,
	}

	existing = frappe.db.get_value("Builder Page", {"route": route}, "name")
	if existing:
		page = frappe.get_doc("Builder Page", existing)
		page.update(fields)
		page.save()
		action = "updated"
	else:
		page = frappe.get_doc(dict(doctype="Builder Page", **fields)).insert()
		action = "created"

	frappe.db.commit()
	print(f"{component_action} Builder Component {component}")
	print(f"{action} Builder Page {page.name} at /{route}")

	return page.name
