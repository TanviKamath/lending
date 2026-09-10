# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Shared block helpers and styles for the borrower portal's Builder pages.

Every visual rule lives on its own block, in baseStyles, because that is the only
styling the Builder canvas reads. The canvas applies baseStyles inline to each element
and never loads the page head_html, so a page styled through a head_html stylesheet
renders as unstyled text there and cannot be arranged by hand. Rules that CSS would
share through one class are therefore repeated per block. That repetition is the price
of a canvas that shows the real page.

Brand colours, fonts and radii stay in Builder Token records, which the canvas does
serve as custom properties, so a bank restyles without touching this file. The palette
holds the Espresso tokens from the installed frappe source, inlined as literals because
:root custom properties declared in head_html do not reach the canvas.
"""

import hashlib

from builder.builder.doctype.builder_token.builder_token import clear_builder_token_cache

import frappe

# A bank overrides these five records. Nothing else in the portal carries brand.
BRAND_TOKENS = [
	{"token_name": "brand-primary", "type": "Color", "value": "#171717", "dark_value": "#f8f8f8"},
	{"token_name": "brand-primary-ink", "type": "Color", "value": "#ffffff", "dark_value": "#171717"},
	{"token_name": "brand-mark", "type": "Color", "value": "#2bb24c", "dark_value": "#2fbe6a"},
	{"token_name": "brand-radius", "type": "Dimension", "value": "8px"},
	{"token_name": "brand-font", "type": "Font", "value": "InterVariable"},
]

# What no block style can carry: the webfont, and the ground behind the page.
HEAD_HTML = """
<!-- Builder Token records are served as :root custom properties by these routes, and the
	Builder canvas serves the same records itself, so var(--brand-*) resolves in the
	editor and on the published page alike. -->
<link rel="stylesheet" href="/builder_assets/tokens.css">
<style>
/* Website pages do not load the desk bundle, so the font ships with the page. */
@font-face {
	font-family: InterVariable;
	font-style: normal;
	font-weight: 100 900;
	font-display: swap;
	src: url("/assets/frappe/css/fonts/inter/InterVariable.woff2") format("woff2");
}

:root { color-scheme: light; }
html { background: #ffffff; }
</style>
"""

# Espresso palette, from frappe/public/css/espresso/.
WHITE = "#ffffff"
GRAY_50 = "#f8f8f8"
GRAY_100 = "#f3f3f3"
GRAY_200 = "#ededed"
GRAY_500 = "#999999"
GRAY_600 = "#7c7c7c"
GRAY_700 = "#525252"
GRAY_900 = "#171717"
GRAY_950 = "#0f0f0f"
GREEN_100 = "#e4faeb"
GREEN_700 = "#14804d"
AMBER_50 = "#fdf8ed"
AMBER_700 = "#bb6f0c"

BORDER = f"1px solid {GRAY_200}"
ACTIVE_SHADOW = "0 0 1px 0 rgba(0, 0, 0, 0.14), 0 1px 3px 0 rgba(0, 0, 0, 0.14)"

# Fragments spread into the style dicts below.
COLUMN = {"display": "flex", "flexDirection": "column"}
ROW_FLEX = {"display": "flex", "alignItems": "center"}
TABULAR = {"fontVariantNumeric": "tabular-nums"}

# Stroked line icons, sized for the 28px rail slot. Inline so the portal pulls in no
# icon font and the glyphs stay editable on the canvas.
ICON = (
	'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
	' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{0}</svg>'
)
ICON_BRAND = ICON.format('<path d="M3 21h18"/><path d="M5 21V10l7-5 7 5v11"/><path d="M10 21v-6h4v6"/>')
ICON_SEARCH = ICON.format('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>')
ICON_BELL = ICON.format(
	'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
)

# var(--brand-font,InterVariable) carries no space after the comma on purpose: Builder
# escapes every space in a fontFamily value, to survive family names like Open Sans.
BODY_STYLES = {
	"margin": "0",
	"background": WHITE,
	"color": GRAY_900,
	"fontFamily": "var(--brand-font,InterVariable)",
	"fontVariationSettings": '"opsz" 24',
	"fontSize": "14px",
	"fontWeight": "420",
	"letterSpacing": "0.02em",
	"lineHeight": "1.5",
	"WebkitFontSmoothing": "antialiased",
}

SHELL_STYLES = {"display": "flex", "minHeight": "100vh", "alignItems": "stretch"}

RAIL_STYLES = {
	**COLUMN,
	"width": "50px",
	"flexShrink": "0",
	"background": GRAY_50,
	"alignItems": "center",
	"gap": "4px",
	"padding": "11px 0 14px",
	"position": "sticky",
	"top": "0",
	"height": "100vh",
}
MARK_STYLES = {
	"width": "28px",
	"height": "28px",
	"borderRadius": "8px",
	"flexShrink": "0",
	"background": "var(--brand-mark,#2bb24c)",
	"color": WHITE,
	"display": "grid",
	"placeItems": "center",
	"marginBottom": "8px",
}
RAIL_DIVIDER_STYLES = {
	"width": "20px",
	"height": "1px",
	"flexShrink": "0",
	"background": GRAY_200,
	"margin": "4px 0",
}
RAIL_ICON_STYLES = {
	"width": "28px",
	"height": "28px",
	"borderRadius": "8px",
	"flexShrink": "0",
	"display": "grid",
	"placeItems": "center",
	"color": GRAY_700,
	"textDecoration": "none",
	"hover:background": GRAY_100,
	"hover:color": GRAY_900,
}
SPACER_STYLES = {"flex": "1 1 auto"}
AVATAR_STYLES = {
	"width": "28px",
	"height": "28px",
	"borderRadius": "999px",
	"flexShrink": "0",
	"background": GREEN_100,
	"color": GREEN_700,
	"display": "grid",
	"placeItems": "center",
	"fontSize": "12px",
	"fontWeight": "600",
}

SIDEBAR_STYLES = {
	**COLUMN,
	"width": "220px",
	"flexShrink": "0",
	"background": GRAY_50,
	"borderRight": BORDER,
	"gap": "12px",
	"padding": "8px 8px 10px 8px",
	"position": "sticky",
	"top": "0",
	"height": "100vh",
}
SIDE_HEAD_STYLES = {
	"padding": "6px 8px 0",
	"fontSize": "15px",
	"fontWeight": "600",
	"color": GRAY_950,
}
SWITCHER_STYLES = {"padding": "6px 8px", "borderRadius": "8px"}
SWITCHER_NAME_STYLES = {"display": "block", "fontSize": "13px", "fontWeight": "500"}
SWITCHER_NOTE_STYLES = {"fontSize": "12px", "color": GRAY_600}

NAV_STYLES = {**COLUMN, "flex": "1 1 auto", "overflowY": "auto", "gap": "2px"}
NAV_ITEM_STYLES = {
	**ROW_FLEX,
	"gap": "10px",
	"padding": "6px 8px",
	"borderRadius": "8px",
	"marginBottom": "1px",
	"fontSize": "13px",
	"color": GRAY_700,
	"textDecoration": "none",
	"hover:background": GRAY_100,
	"hover:color": GRAY_900,
}
NAV_ITEM_ACTIVE_STYLES = {
	**NAV_ITEM_STYLES,
	"background": WHITE,
	"color": GRAY_900,
	"fontWeight": "500",
	"boxShadow": ACTIVE_SHADOW,
}

SIDE_FOOT_STYLES = {"padding": "10px 8px 0", "borderTop": BORDER}
SIDE_FOOT_NAME_STYLES = {"display": "block", "fontSize": "13px", "fontWeight": "500"}
SIDE_FOOT_NOTE_STYLES = {"fontSize": "12px", "color": GRAY_600}

MAIN_STYLES = {**COLUMN, "flex": "1 1 auto", "minWidth": "0"}

PAGE_HEAD_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"flexWrap": "wrap",
	"minHeight": "48px",
	"padding": "0 20px",
	"borderBottom": BORDER,
}
CRUMB_STYLES = {
	"fontSize": "16px",
	"fontWeight": "500",
	"color": GRAY_950,
	"letterSpacing": "0.015em",
}
HEAD_NOTE_STYLES = {"fontSize": "13px", "color": GRAY_700}
HEAD_END_STYLES = {**ROW_FLEX, "marginLeft": "auto", "gap": "10px"}
STATUS_STYLES = {**ROW_FLEX, "gap": "6px", "fontSize": "13px", "color": GRAY_700}
STATUS_DOT_STYLES = {
	"width": "6px",
	"height": "6px",
	"borderRadius": "999px",
	"background": GREEN_700,
}
BTN_STYLES = {
	"fontFamily": "inherit",
	"fontSize": "13px",
	"fontWeight": "500",
	"cursor": "pointer",
	"padding": "6px 12px",
	"borderRadius": "var(--brand-radius,8px)",
	"border": "1px solid transparent",
	"whiteSpace": "nowrap",
	"textDecoration": "none",
	"background": "var(--brand-primary,#171717)",
	"color": "var(--brand-primary-ink,#ffffff)",
	"hover:filter": "brightness(1.4)",
}

CONTENT_STYLES = {**COLUMN, "flex": "1 1 auto", "padding": "20px", "gap": "20px"}
CARDS_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(auto-fit, minmax(240px, 1fr))",
	"gap": "20px",
}
NCARD_STYLES = {
	**COLUMN,
	"minHeight": "110px",
	"padding": "12px",
	"background": WHITE,
	"border": BORDER,
	"borderRadius": "12px",
}
NCARD_HEAD_STYLES = {
	"display": "flex",
	"justifyContent": "space-between",
	"alignItems": "flex-start",
	"gap": "8px",
}
NCARD_TITLE_STYLES = {"fontSize": "13px", "fontWeight": "500"}
NCARD_BODY_STYLES = {**COLUMN, "paddingTop": "12px"}
NUMBER_STYLES = {
	**TABULAR,
	"fontSize": "18px",
	"fontWeight": "600",
	"letterSpacing": "0.01em",
	"lineHeight": "115%",
}
NCARD_STAT_STYLES = {**TABULAR, "marginTop": "10px", "fontSize": "13px", "color": GRAY_700}

# The two-column split folds to one column on Builder's tablet breakpoint (<=1023px).
GRID_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "minmax(0, 1.9fr) minmax(0, 1fr)",
	"gap": "20px",
	"alignItems": "start",
}
GRID_TABLET_STYLES = {"gridTemplateColumns": "minmax(0, 1fr)"}

STACK_STYLES = {**COLUMN, "gap": "20px", "minWidth": "0"}
CARD_STYLES = {
	**COLUMN,
	"background": WHITE,
	"border": BORDER,
	"borderRadius": "12px",
	"minWidth": "0",
}
CARD_HEAD_STYLES = {"padding": "12px 12px 14px"}
CARD_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "16px",
	"fontWeight": "600",
	"color": GRAY_950,
	"lineHeight": "1.3em",
	"letterSpacing": "0.015em",
}
CARD_SUB_STYLES = {**TABULAR, "marginTop": "5px", "fontSize": "14px", "color": GRAY_700}

THEAD_STYLES = {**ROW_FLEX, "gap": "12px", "padding": "0 12px 8px", "borderBottom": BORDER}
THEAD_LABEL_STYLES = {"fontSize": "12px", "color": GRAY_600}
ROW_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"padding": "12px",
	"borderTop": BORDER,
	"hover:background": GRAY_50,
}
COL_MAIN_STYLES = {**COLUMN, "flex": "1 1 auto", "minWidth": "0", "gap": "2px"}
COL_STATUS_STYLES = {"width": "150px", "flexShrink": "0"}
COL_NEXT_STYLES = {**COLUMN, "width": "120px", "flexShrink": "0", "gap": "2px"}
COL_AMT_STYLES = {
	**COLUMN,
	"width": "150px",
	"flexShrink": "0",
	"textAlign": "right",
	"gap": "2px",
}

PRIMARY_TEXT_STYLES = {"fontSize": "13px", "fontWeight": "500"}
SECONDARY_TEXT_STYLES = {**TABULAR, "fontSize": "12px", "color": GRAY_600}
AMOUNT_STYLES = {**TABULAR, "fontSize": "13px", "fontWeight": "500"}

STATE_STYLES = {
	"display": "inline-flex",
	"alignItems": "center",
	"gap": "6px",
	"fontSize": "13px",
	"color": GRAY_700,
}
DOT_STYLES = {
	"width": "6px",
	"height": "6px",
	"borderRadius": "999px",
	"background": GRAY_500,
	"flexShrink": "0",
}
FLAG_STYLES = {
	"display": "inline-block",
	"fontSize": "12px",
	"fontWeight": "500",
	"color": AMBER_700,
	"background": AMBER_50,
	"padding": "2px 8px",
	"borderRadius": "4px",
}
WHY_STYLES = {"fontSize": "12px", "color": AMBER_700}

LI_STYLES = {
	"display": "flex",
	"alignItems": "baseline",
	"gap": "12px",
	"padding": "12px",
	"borderTop": BORDER,
}
LI_DATE_STYLES = {
	**TABULAR,
	"width": "80px",
	"flexShrink": "0",
	"fontSize": "13px",
	"color": GRAY_700,
}
LI_BODY_STYLES = {**COLUMN, "flex": "1 1 auto", "minWidth": "0", "gap": "2px"}
LI_AMT_STYLES = {**TABULAR, "flexShrink": "0", "fontSize": "13px", "fontWeight": "500"}

FOOTER_STYLES = {
	**ROW_FLEX,
	"gap": "20px",
	"flexWrap": "wrap",
	"padding": "14px 20px",
	"borderTop": BORDER,
	"fontSize": "12px",
	"color": GRAY_600,
}
FOOTER_LINK_STYLES = {
	"color": GRAY_700,
	"textDecoration": "none",
	"marginRight": "18px",
	"hover:color": GRAY_900,
}

# The rail and the sidebar leave the page on Builder's mobile breakpoint (<=576px).
HIDDEN = {"display": "none"}

def empty_block_fields() -> dict:
	"""The style and attribute slots every block carries, fresh each call.

	A module-level constant would hand the same dict to every block, so one later
	mutation would leak across the whole tree.
	"""
	return {
		"baseStyles": {},
		"mobileStyles": {},
		"tabletStyles": {},
		"attributes": {},
		"customAttributes": {},
		"classes": [],
	}


def block_id(path: str) -> str:
	"""A block id derived from its position, not from chance.

	The shell lives in a Builder Component, and a page that uses it must mirror the
	component's tree with a referenceBlockId per node. Random ids would stop matching
	the moment either side is regenerated, so the id is a digest of the path instead:
	the same tree always yields the same ids, and a rebuild stays compatible with the
	pages already pointing at it.
	"""
	return hashlib.blake2s(path.encode(), digest_size=5).hexdigest()[:9]


def block(element, styles=None, children=None, html=None, path=None, **kwargs):
	"""One block as a plain dict, styled on the block so the canvas can show it."""
	node = {
		"blockId": block_id(path) if path else frappe.generate_hash(length=9),
		"element": element,
		**empty_block_fields(),
		"baseStyles": dict(styles or {}),
		"children": list(children or []),
	}
	# stub() addresses component nodes by path; strip_paths() drops it before storing.
	if path:
		node["path"] = path
	node.update(kwargs)
	if html is not None:
		node["innerHTML"] = html

	return node


def bind(node, key, property="innerHTML", type="key"):
	"""Point one of a block's properties at a key from the page data script.

	type "key" writes the value into the property itself, which is how text arrives.
	type "attribute" writes it into the rendered tag's attributes, which is how a
	repeated row gets its own href.
	"""
	node.setdefault("dynamicValues", []).append(
		{"key": key, "type": type, "property": property, "comesFrom": "dataScript"}
	)

	return node


def bound(element, key, styles=None, path=None, **kwargs):
	"""A block whose text comes from the page data script."""
	return bind(block(element, styles=styles, path=path, **kwargs), key)


def linked(key, styles=None, children=None, **kwargs):
	"""A row that carries its own destination, for a repeater over records."""
	node = block("a", styles=styles, children=children, attributes={"href": "#"}, **kwargs)
	return bind(node, key, property="href", type="attribute")


def repeater(key, row, path=None):
	node = block("div", path=path, isRepeaterBlock=True, children=[row])
	node["dataKey"] = {"key": key, "type": "key", "property": "dataKey", "comesFrom": "dataScript"}

	return node


def upsert_tokens():
	"""Create the brand tokens under readable, stable document names.

	Builder Token.autoname only falls back to a UUID when no name is set, and the
	emitted CSS custom property is --<document name>. Naming them after the token
	gives every site the same --brand-* properties, so the references above are
	portable; left to autoname, each site would emit a different UUID.
	"""
	for token in BRAND_TOKENS:
		name = token["token_name"]

		if frappe.db.exists("Builder Token", name):
			doc = frappe.get_doc("Builder Token", name)
			doc.update(token)
			doc.save()
			continue

		# drop any earlier UUID-named copy of the same token
		for stale in frappe.get_all("Builder Token", filters={"token_name": name}, pluck="name"):
			frappe.delete_doc("Builder Token", stale, force=True, ignore_permissions=True)

		doc = frappe.new_doc("Builder Token")
		doc.update(token)
		doc.insert()

		# frappe.model.naming.set_new_name clears an explicitly assigned name unless the
		# doctype autonames by prompt or uuid, so the rename has to follow the insert.
		if doc.name != name:
			frappe.rename_doc("Builder Token", doc.name, name, force=True, show_alert=False)

	clear_builder_token_cache()


def card(title, subtitle_key, body):
	"""A titled panel with a subtitle from data. Every portal page is built of these."""
	return block(
		"section",
		styles=CARD_STYLES,
		children=[
			block(
				"div",
				styles=CARD_HEAD_STYLES,
				children=[
					block("h2", styles=CARD_TITLE_STYLES, html=title),
					bound("div", subtitle_key, styles=CARD_SUB_STYLES),
				],
			),
			body,
		],
	)


def pair_rows(key, with_detail=False, marker=False):
	"""A repeater over {label, value, detail} rows -- the portal's workhorse shape."""
	main = [
		bound("div", "label", styles=SECONDARY_TEXT_STYLES),
		bound("div", "value", styles=PRIMARY_TEXT_STYLES),
	]
	if with_detail:
		detail = bound("div", "detail", styles=SECONDARY_TEXT_STYLES)
		detail["visibilityCondition"] = "detail"
		main.append(detail)

	children = []
	if marker:
		children.append(
			bound("span", "marker", styles={**AVATAR_STYLES, "background": "transparent"})
		)
	children.append(block("div", styles=COL_MAIN_STYLES, children=main))

	return repeater(key, block("div", styles=ROW_STYLES, children=children))


def note_panel(key):
	"""A quiet line of guidance under a card, shown only when the data supplies one."""
	node = bound("div", key, styles={**SECONDARY_TEXT_STYLES, "padding": "12px"})
	node["visibilityCondition"] = key

	return node


# --- the public pages: no sidebar, one centred column -----------------------------

PUBLIC_PAGE_STYLES = {
	**COLUMN,
	"minHeight": "100vh",
	"alignItems": "center",
	"padding": "40px 20px",
	"gap": "20px",
	"background": GRAY_50,
}
PUBLIC_COLUMN_STYLES = {**COLUMN, "width": "100%", "maxWidth": "560px", "gap": "20px"}
PUBLIC_BRAND_STYLES = {**ROW_FLEX, "gap": "10px"}
PUBLIC_HEADING_STYLES = {
	"margin": "0",
	"fontSize": "24px",
	"fontWeight": "600",
	"color": GRAY_950,
	"letterSpacing": "0.01em",
}
PUBLIC_INTRO_STYLES = {"fontSize": "14px", "color": GRAY_700, "lineHeight": "1.55"}

FIELD_STYLES = {**COLUMN, "gap": "4px", "padding": "8px 12px"}
LABEL_STYLES = {"fontSize": "12px", "fontWeight": "500", "color": GRAY_700}
INPUT_STYLES = {
	"fontFamily": "inherit",
	"fontSize": "14px",
	"padding": "8px 10px",
	"borderRadius": "var(--brand-radius,8px)",
	"border": BORDER,
	"background": WHITE,
	"color": GRAY_900,
	"width": "100%",
	"boxSizing": "border-box",
}
SUBMIT_ROW_STYLES = {**ROW_FLEX, "gap": "10px", "padding": "12px", "borderTop": BORDER}
RESULT_STYLES = {
	**COLUMN,
	"gap": "8px",
	"padding": "16px",
	"background": GREEN_100,
	"borderRadius": "12px",
	"color": GRAY_900,
}
ERROR_STYLES = {
	"padding": "12px 16px",
	"background": AMBER_50,
	"borderRadius": "8px",
	"fontSize": "13px",
	"color": AMBER_700,
}


def field(label, name, input_type="text", placeholder="", required=True):
	"""One labelled input. The name is what the client script posts."""
	attributes = {"name": name, "type": input_type, "placeholder": placeholder or label}
	if required:
		attributes["required"] = "required"

	return block(
		"div",
		styles=FIELD_STYLES,
		children=[
			block("label", styles=LABEL_STYLES, html=label),
			block("input", styles=INPUT_STYLES, attributes=attributes),
		],
	)


def select_field(label, name, options_key):
	"""A select whose options come from the data script, one <option> per row."""
	option = bound("option", "label", styles={})
	bind(option, "value", property="value", type="attribute")

	return block(
		"div",
		styles=FIELD_STYLES,
		children=[
			block("label", styles=LABEL_STYLES, html=label),
			block(
				"select",
				styles=INPUT_STYLES,
				attributes={"name": name, "required": "required"},
				children=[repeater(options_key, option)],
			),
		],
	)


def public_frame(heading_key, intro_key, children):
	"""The public shell: brand, heading, then whatever the page is for."""
	return block(
		"div",
		styles=PUBLIC_PAGE_STYLES,
		children=[
			block(
				"div",
				styles=PUBLIC_COLUMN_STYLES,
				children=[
					block(
						"div",
						styles=PUBLIC_BRAND_STYLES,
						children=[
							block("span", styles=MARK_STYLES, html=ICON_BRAND),
							bound("span", "brand_name", styles={"fontSize": "15px", "fontWeight": "600"}),
						],
					),
					block("h1", styles=PUBLIC_HEADING_STYLES, children=[bound("span", heading_key)]),
					bound("p", intro_key, styles=PUBLIC_INTRO_STYLES),
					*children,
				],
			)
		],
	)
