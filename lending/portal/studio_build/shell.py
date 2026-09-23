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
	fallback,
	instance,
	muted,
	repeater,
	root,
	row,
	spacer,
	text,
)

HEADER = "borrower_header"
FOOTER = "borrower_footer"
ALERTS = "borrower_alerts"

# The crumb trail, as frappe-ui draws one. `Breadcrumbs.vue` gives every crumb
# `px-0.5 py-1 text-lg-medium`, colours the trail `ink-gray-5` and the last one
# `ink-gray-9`, and sets `/` between them in `text-base ink-gray-4` with `mx-0.5`.
#
# `text-lg-medium` is named rather than unpacked into numbers: the portal's own bundle
# carries the class, so the header takes 16px/500/1.15/0.015em from the same rule the
# desk reads it from, and follows it if the scale is ever retuned. Only what a Studio
# block cannot say as a class -- the padding and the two colours -- is spelled out.
CRUMB_TYPE = "text-lg-medium"
CRUMB_BOX = {"display": "flex", "alignItems": "center", "padding": "4px 2px"}

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

# Whether the rail is open, as every block in it has to ask.
#
# frappe-ui's Sidebar provides its collapsed state down the tree and its own parts inject
# it; blocks cannot inject anything, so the state is bound out to a page-script ref
# instead -- `collapsed` is a v-model on Sidebar -- and read back through this. Anything
# that is words rather than a glyph leaves the rail while it is shut, rather than being
# clipped by the 48px of it that remain.
#
# The ref starts as null, which is Sidebar's own "collapse on mobile, otherwise not", so
# the second half reads as open until somebody presses the toggle.
#
# The `typeof` guard is what makes the rail survive the Studio canvas. An expression is
# evaluated as `with (context) { return <expr> }`, and the canvas has no context to put
# `sidebarCollapsed` in: a page's bindings come from importing its built setup() module,
# which the editor cannot do for an exported app. A bare `!sidebarCollapsed` is then a
# ReferenceError, the evaluator answers undefined, and `visibilityCondition` reads that
# as false -- so every word in the rail vanished on the canvas while the running portal
# was fine. `typeof` is the one operator that does not throw on a name that was never
# declared, so it answers "undefined" there and the real value everywhere else.
EXPANDED = "{{ typeof sidebarCollapsed === 'undefined' || !sidebarCollapsed }}"

# The same question the other way about, for the blocks that want it that way. Written
# out rather than negating the one above: `!` in front of that guard would make the
# canvas, where the name does not exist, read as shut rather than open.
COLLAPSED = "typeof sidebarCollapsed !== 'undefined' && sidebarCollapsed"

# The square the lender's mark is drawn in, whichever of the two marks it turns out to
# be. The numbers are SidebarHeader's own -- `size-7` at `rounded-[6px]`.
MARK = {"width": "28px", "height": "28px", "flexShrink": "0", "borderRadius": "6px"}


def brand(data):
	"""Whose portal this is: the lender's mark, and the lender's name beside it.

	Not frappe-ui's SidebarHeader. That one is the trigger of a Dropdown and draws the
	chevron that opens it whether or not the menu holds anything, and no prop takes the
	chevron away. This portal has nothing to put in that menu -- one app, one borrower,
	no workspace to switch to -- so the header is the two pieces the desk's own header is
	made of, and none of it is pressable.

	Both marks are written out, and one of them renders: `brand_payload` carries the logo
	and the name together because the page is built once and Lending Settings is read per
	request, so the page cannot know which it will have. `show_wordmark` is that payload's
	own answer to which one this is.
	"""
	logo = block(
		"ImageView",
		props={"image": "{{ %s.brand_logo }}" % data, "alt": "", "shape": "square", "size": "lg"},
		# ImageView's own sizes start at 128px, for a picture on a page rather than a mark
		# in a rail. The styles win over the classes that set them, so `size` here is only
		# choosing the 6px corner that goes with it.
		styles=dict(MARK, overflow="hidden"),
		visible="{{ %s.brand_logo }}" % data,
	)
	letter = text(
		"{{ (%s.brand_name || '').charAt(0) }}" % data,
		size="text-base",
		styles=dict(
			MARK,
			display="flex",
			alignItems="center",
			justifyContent="center",
			textTransform="uppercase",
			backgroundColor="var(--surface-gray-4)",
			color="var(--ink-gray-7)",
		),
		visible="{{ %s.show_wordmark }}" % data,
	)

	# `flex: 1` is what lets one row serve both states. Open, the name fills the row and
	# the mark is pushed to the left edge regardless of the centring below; shut, the name
	# is gone and the mark is the only thing left to centre.
	name = text(
		fallback("{{ %s.brand_name }}" % data, "''"),
		size="text-base",
		styles={
			"flex": "1 1 0%",
			"fontWeight": "500",
			"color": "var(--ink-gray-8)",
			"minWidth": "0px",
			"overflow": "hidden",
			"textOverflow": "ellipsis",
			"whiteSpace": "nowrap",
		},
		visible=EXPANDED,
	)

	# 48px tall, so the mark sits in the same band as the page header beside it, and 6px
	# in from a rail already padded 8, which is where SidebarHeader's own px-1 + px-1.5
	# put it. Shut, those 6px leave less room than the mark needs and it overflows them
	# evenly either side -- which is the rail's centre, 8 + 6 + 10 of 48.
	#
	# So the centring is load-bearing only once the name has gone, and it reads as a bug
	# the moment the name goes for any other reason: the mark drifts to the middle of an
	# open rail. See EXPANDED for the one that did it.
	return row(
		[logo, letter, name],
		gap="8px",
		styles={"height": "48px", "flexShrink": "0", "justifyContent": "center", "padding": "0 6px"},
	)


def collapse_toggle():
	"""The one control that shuts the rail, drawn where the desk draws it.

	The desk hangs a 24px disc off the sidebar's right edge, half of it out over the
	border, and keeps it invisible until the pointer is somewhere on the sidebar. That is
	the whole affordance: no row in the list, nothing holding space in the column, and
	nothing to read. `SidebarCollapseToggle`, which is a labelled row at the foot of the
	list, is what this replaces.

	Two things a style cannot say are said as classes instead -- appearing on hover of an
	ancestor, and the hover of the disc itself. Tailwind generates both from the exported
	page JSON, because studio's content glob reaches into every app's studio folder, so
	neither has to exist in studio's own source first.
	"""
	return button(
		"",
		script="sidebarCollapsed.value = !sidebarCollapsed.value",
		variant="ghost",
		props={
			"icon": "{{ %s ? 'lucide-chevron-right' : 'lucide-chevron-left' }}" % COLLAPSED,
			"label": "Toggle sidebar",
			"size": "xs",
		},
		classes=[
			"opacity-0",
			"group-hover:opacity-100",
			"transition-opacity",
			# `!` because the resting background below is an inline style, and an
			# important declaration in a stylesheet is the only thing that outranks one.
			"hover:!bg-surface-gray-2",
		],
		# `xs` is already the desk's 24px; everything here is the disc the desk cuts out
		# of that square, and where it hangs. -12px is half of it, so it straddles the
		# border rather than sitting inside the rail.
		styles={
			"position": "absolute",
			"right": "-12px",
			"bottom": "80px",
			"borderRadius": "9999px",
			"borderWidth": "1px",
			"borderStyle": "solid",
			"borderColor": "var(--outline-gray-1)",
			"backgroundColor": "var(--surface-sidebar)",
			"boxShadow": "0 1px 4px rgba(0, 0, 0, 0.1)",
		},
	)


def sidebar(data):
	"""The list of pages, and whose portal it is.

	Laid out as the desk's own sidebar is, which mostly meant leaving it alone: the two
	already agree on the row, down to the number. `text-sm` is 13px at 420 over 1.15 in
	both scales; SidebarItem's `h-7` is the desk's 28px anchor; the label is `ink-gray-6`
	in both; `rounded` resolves to `--radius-4`, which is the desk's 8px; both hover at
	gray-100 and draw the row you are on in white under a small shadow. What the desk has
	and this did not is the hairline down the right of the rail, a header with nothing to
	press, and the disc on the edge that shuts it -- see `collapse_toggle`.

	One thing is deliberately not the desk's. There, collapsing takes the sidebar away
	entirely and the workspace dock becomes the icon rail you reopen it from. This portal
	has no dock, so a rail that left would leave nothing to press to bring it back; it
	keeps frappe-ui's 48px of icons instead, and the disc rides along on that.
	"""
	foot = column(
		[
			text("{{ %s.holder_name }}" % data, size="text-sm", styles={"fontWeight": "600"}),
			muted("{{ %s.customer_note }}" % data),
		],
		gap="2px",
		styles={"padding": "12px"},
		visible=EXPANDED,
	)

	nav_items = [
		block("SidebarItem", props={"label": title, "icon": "lucide-%s" % icon, "to": route})
		for title, route, icon in NAV_ITEMS
	]

	sidebar_children = [
		block(
			"div",
			styles={"display": "flex", "height": "100%", "flexDirection": "column", "padding": "0.5rem"},
			children=[
				brand(data),
				block(
					"div",
					styles={"flex": "1 1 0%", "overflowY": "auto", "overflowX": "hidden"},
					children=nav_items,
				),
				block("div", styles={"marginTop": "auto"}, children=[foot]),
			],
		),
		collapse_toggle(),
	]

	# The border is frappe-ui's own `border-r border-outline-gray-1`, which Sidebar draws
	# only for the config-object API it is keeping around for one more release. Written
	# out here because this sidebar is composed rather than configured, and because
	# `--outline-gray-1` is #ededed, which is the desk's `--sidebar-border-color` exactly.
	#
	# The other three all serve the disc on the edge. `relative` is what it is positioned
	# against; `overflow-x` has to be given back, because Sidebar hides it and would cut
	# the disc off at the border it is meant to straddle -- nothing else in the rail
	# reaches the edge, since every label clips itself as it collapses; and `group` is the
	# ancestor whose hover reveals it.
	return block(
		"Sidebar",
		props={"collapsed": {"$type": "variable", "name": "sidebarCollapsed"}},
		children=sidebar_children,
		classes=["group"],
		styles={
			"position": "relative",
			"overflowX": "visible",
			"borderRight": "1px solid var(--outline-gray-1)",
		},
		mobile={"display": "none"},
	)


def header_tree():
	"""The crumb, the day it is being read, and the one thing the page offers to press.

	Every value arrives as an input, so one header serves ten pages. The action hides
	itself where a page passes no label -- the statement and the certificate keep their
	download inside the page, beside the dates it obeys.
	"""
	crumb_node = row(
		[
			text(
				"{{ dataItem.label }}",
				size=CRUMB_TYPE,
				styles={**CRUMB_BOX, "color": "var(--ink-gray-5)", "cursor": "pointer"},
				classes=["hover:text-ink-gray-7"],
				events=click("open(dataItem.route)"),
				visible="{{ dataItem.route }}"
			),
			text(
				"{{ dataItem.label }}",
				size=CRUMB_TYPE,
				styles={
					**CRUMB_BOX,
					"color": "var(--ink-gray-9)",
					"minWidth": "0px",
					"overflow": "hidden",
					"textOverflow": "ellipsis",
					"whiteSpace": "nowrap",
				},
				visible="{{ !dataItem.route }}"
			),
			text(
				"/",
				size="text-base",
				styles={"margin": "0px 2px", "color": "var(--ink-gray-4)"},
				visible="{{ dataItem.route }}"
			),
		],
		gap="0px",
		styles={"alignItems": "center", "minWidth": "0px"}
	)

	breadcrumbs = repeater(
		"{{ inputs.breadcrumbs }}",
		crumb_node,
		# No gap: frappe-ui sets the crumbs flush against each other and lets the `/` hold
		# them apart on its own -- `mx-0.5` on the separator against `px-0.5` on the crumb
		# either side of it, so 4px of white each way. Zero has to be said out loud, since
		# Studio's Repeater carries `gap-5` on its own wrapper and would stand them 20px
		# apart on its own.
		styles={
			"display": "flex",
			"flexDirection": "row",
			"alignItems": "center",
			"minWidth": "0px",
			"gap": "0px",
		},
		visible="{{ inputs.breadcrumbs && inputs.breadcrumbs.length > 0 }}"
	)

	# A page with no trail says its own name, as frappe-ui's PageHeaderTitle does:
	# `truncate text-lg font-semibold text-ink-gray-9`. `text-lg` rather than
	# `text-lg-semibold` -- the weight is overridden on top of the regular style, so the
	# tracking stays the regular 0.02em, and copying the semibold style would tighten it.
	titles = text(
		"{{ inputs.crumb }}",
		tag="h1",
		size="text-lg",
		styles={
			"fontWeight": "600",
			"color": "var(--ink-gray-9)",
			"minWidth": "0px",
			"overflow": "hidden",
			"textOverflow": "ellipsis",
			"whiteSpace": "nowrap",
		},
		visible="{{ !inputs.breadcrumbs || inputs.breadcrumbs.length === 0 }}"
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

	# The badge sits beside the record it describes, not out at the right margin: it
	# reads as part of the title. `gap-2` between them, as the desk header has it --
	# 10px apart on the page, once the last crumb's own 2px of padding is counted.
	return row(
		[
			row(
				[breadcrumbs, titles, status],
				gap="8px",
				styles={"alignItems": "center", "minWidth": "0px"},
			),
			spacer(),
			bell,
			action,
		],
		gap="10px",
		styles={
			"padding": "0px",
			# Set on the canvas rather than here, and carried back so a rebuild keeps it.
			# frappe-ui's own header pads `px-3 sm:px-5`, and the content below this one
			# sits at 20px, so 20 is what would line the crumb up with the cards.
			"paddingLeft": "15px",
			"width": "100%",
			"minHeight": "48.8px",
			"alignItems": "center",
			# The rule under the header, as `PageHeader.vue` draws it: plain `border-b`,
			# whose colour is the preset's own `borderColor.DEFAULT`. Spelled out rather
			# than left to the class, because that default is set on Tailwind's preflight
			# rule and a block styled here carries no class to inherit it from.
			"borderBottom": "1px solid var(--outline-gray-1)",
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
			# A fixed 49px band, matching the 48.8px header at the other end of the page.
			# The vertical padding goes with it: the links are `sm` buttons, 28px tall, and
			# 12px either side of them would ask for 52px in a box that is only allowed 49.
			"height": "49px",
			"flexShrink": "0",
			"padding": "0px 20px",
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
			("breadcrumbs", "List of breadcrumbs"),
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
			"breadcrumbs": "{{ %s.breadcrumbs }}" % data,
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
