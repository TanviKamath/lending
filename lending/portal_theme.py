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

/* Every block carries its display inline, which outranks the browser's own
	[hidden] { display: none } rule. Without this, hiding a panel does nothing. */
[hidden] { display: none !important; }

/* State and interaction, which a block's inline styles cannot express. A block can
	carry its own :hover through a "hover:property" style key, but the chosen tile and
	the filled code box are states the script sets on an attribute, so the appearance
	of a choice lives here rather than in the script. */
input:focus-visible, select:focus-visible, button:focus-visible, a:focus-visible {
	outline: 2px solid #0f0f0f; outline-offset: 2px;
}
input:focus, select:focus { border-color: #0f0f0f; }
[data-code] input:not(:placeholder-shown) { border-color: #0f0f0f; }

/* The tiles are this page's radio buttons, at the size the question deserves. The
	dot is the smallest part of the control, so choosing one restyles the whole tile. */
[data-tile][data-chosen="1"] {
	border-color: #0f0f0f; box-shadow: inset 0 0 0 1px #0f0f0f;
}
[data-tile][data-chosen="1"] [data-tile-icon] { background: #0f0f0f; color: #ffffff; }
[data-tile][data-chosen="1"] [data-tile-radio] {
	background: #0f0f0f; border-color: #0f0f0f;
}
[data-tile-icon] svg { width: 19px; height: 19px; }
[data-tile-radio] svg { width: 13px; height: 13px; }
[data-echo-note] svg { width: 13px; height: 13px; }

/* The tick is always in the dot, so the dot never changes size when it is chosen. */
[data-tile-radio] svg { opacity: 0; }
[data-tile][data-chosen="1"] [data-tile-radio] svg { opacity: 1; }

/* A step whose question is unanswered offers a button that cannot be pressed, which
	is quieter than letting it through and then refusing the form. */
button[disabled], button[disabled]:hover { opacity: 0.45; cursor: default; filter: none; }

/* The sidebar's collapse toggle. Out of the way until the pointer is over the
	sidebar, and always in reach while the sidebar is shut, because a control that
	hides the menu has to be the control that brings it back. */
[data-sidebar-toggle] { opacity: 0; transition: opacity 120ms ease, transform 160ms ease; }
[data-sidebar]:hover [data-sidebar-toggle],
[data-sidebar-toggle]:focus-visible { opacity: 1; }

[data-sidebar][data-collapsed="1"] {
	width: 0; min-width: 0; padding-left: 0; padding-right: 0; border-right-color: transparent;
}
/* Every row carries its display inline, so hiding the list needs to outrank that.
	The toggle is the one child that stays. */
[data-sidebar][data-collapsed="1"] > *:not([data-sidebar-toggle]) { display: none; }
[data-sidebar][data-collapsed="1"] [data-sidebar-toggle] { opacity: 1; transform: rotate(180deg); }

/* The offer grid is three columns of figures. Two of them on a phone would wrap
	mid-number, so it drops to one. */
@media (max-width: 600px) {
	[data-offer-grid] { grid-template-columns: minmax(0, 1fr); }
}
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
BLACK = GRAY_900  # the same darkest ink, for the places that mean black rather than a gray
GREEN_100 = "#e4faeb"
GREEN_700 = "#14804d"
RED_600 = "#ce2c2c"
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
ICON_PERSON = ICON.format('<circle cx="12" cy="8" r="4"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/>')
ICON_COMPANY = ICON.format(
	'<rect x="2" y="7" width="20" height="14" rx="2"/>'
	'<path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M2 13h20"/>'
)
ICON_MONEY = ICON.format(
	'<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>'
	'<path d="M6 12h.01"/><path d="M18 12h.01"/>'
)
ICON_CHECK = ICON.format('<path d="m5 13 4 4 10-10"/>')
CHEVRON_LEFT = ICON.format('<path d="m15 18-6-6 6-6"/>')
CHEVRON_RIGHT = ICON.format('<path d="m9 18 6-6-6-6"/>')

# The brand font first, then what to fall back on. The webfont is one request away
# from not arriving, and a page that then renders in the browser's default serif does
# not look like the same product.
#
# No space follows any comma, on purpose. Builder escapes every space in a fontFamily
# value so that family names like Open Sans survive, and it escapes them everywhere:
# a space after a comma would be escaped into the start of the next family's name, and
# "\ sans-serif" is a family nobody has rather than the generic keyword. The families
# that need an internal space are quoted instead, where an escaped space is still a
# space. var(--brand-font) supplies only the first family, so a bank that overrides the
# token keeps these fallbacks behind whatever it chooses.
FONT_STACK = ",".join(
	(
		"var(--brand-font,InterVariable)",
		"Inter",
		"-apple-system",
		"BlinkMacSystemFont",
		'"Segoe UI"',
		"Roboto",
		"Oxygen",
		"Ubuntu",
		"Cantarell",
		'"Fira Sans"',
		'"Droid Sans"',
		'"Helvetica Neue"',
		"sans-serif",
	)
)

BODY_STYLES = {
	"margin": "0",
	"background": WHITE,
	"color": GRAY_900,
	"fontFamily": FONT_STACK,
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
	# sticky is a positioned element, which is what the collapse toggle hangs off.
	"position": "sticky",
	"top": "0",
	"height": "100vh",
	"transition": "width 160ms ease, padding 160ms ease",
}
# The toggle sits astride the sidebar's own border, half in and half out, so it reads
# as belonging to the edge rather than to the list. It rides low on that edge, the way
# the desk sidebar's own toggle does, which keeps it clear of the first nav rows and
# puts it where someone who has used the desk already looks for it. 62px lands it just
# above the foot's rule. It is furniture: the rules that show it on hover and keep it
# in reach once the sidebar is shut are in HEAD_HTML, which the canvas does not load,
# so the button stays visible and editable there.
SIDE_COLLAPSE_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"position": "absolute",
	"bottom": "62px",
	"right": "-13px",
	"width": "26px",
	"height": "26px",
	"padding": "0",
	"borderRadius": "999px",
	"border": BORDER,
	"background": WHITE,
	"boxShadow": ACTIVE_SHADOW,
	"color": GRAY_700,
	"cursor": "pointer",
	"zIndex": "30",
	"hover:color": GRAY_950,
	"hover:borderColor": GRAY_500,
}
# One treatment for every line in the sidebar, so the whole rail reads as a single
# list rather than as six kinds of text. The rows that need to stand out -- the one
# you are on, the one under the pointer -- do it with a card and a colour, not with a
# size or a weight of their own. The two names are <b> elements, so the weight has to
# be said out loud to beat the browser's bold.
SIDE_TEXT_STYLES = {"fontSize": "13px", "fontWeight": "420", "color": GRAY_700}

# The one line that is not a row in the list: it says whose portal this is.
SIDE_HEAD_STYLES = {
	**SIDE_TEXT_STYLES,
	"fontSize": "14px",
	"fontWeight": "500",
	"color": BLACK,
	"padding": "6px 8px 0",
}

NAV_STYLES = {**COLUMN, "flex": "1 1 auto", "overflowY": "auto", "gap": "2px"}
NAV_ITEM_STYLES = {
	**ROW_FLEX,
	"gap": "10px",
	"padding": "6px 8px",
	"borderRadius": "8px",
	"marginBottom": "1px",
	**SIDE_TEXT_STYLES,
	"textDecoration": "none",
	"hover:background": GRAY_100,
	"hover:color": GRAY_900,
}
# The white card and its shadow are the whole of the active state now.
NAV_ITEM_ACTIVE_STYLES = {**NAV_ITEM_STYLES, "background": WHITE, "boxShadow": ACTIVE_SHADOW}

# The foot is the last line inside a box that is exactly 100vh tall, so it is the one
# place in the sidebar where text meets a hard edge with nothing under it. On a display
# at 125% or 150% scaling, 100vh lands on a fractional pixel and the bottom of that line
# is shaved off. Four pixels under it is enough that the rounding never reaches the type.
SIDE_FOOT_STYLES = {"padding": "10px 8px 4px", "borderTop": BORDER}
SIDE_FOOT_NAME_STYLES = {**SIDE_TEXT_STYLES, "display": "block"}
SIDE_FOOT_NOTE_STYLES = dict(SIDE_TEXT_STYLES)

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

# A little more room at the foot than at the head: the last card ends against the
# footer's rule, and a page that stops dead on its last line reads as cut off.
CONTENT_STYLES = {**COLUMN, "flex": "1 1 auto", "padding": "20px 20px 28px", "gap": "20px"}
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
# A head that carries a control: the titles take the room they need and the control
# sits against the right edge, dropping under them when there is no room for both.
CARD_HEAD_ROW_STYLES = {
	**CARD_HEAD_STYLES,
	**ROW_FLEX,
	"alignItems": "flex-start",
	"flexWrap": "wrap",
	"gap": "10px",
}
CARD_TITLES_STYLES = {**COLUMN, "flex": "1 1 auto", "minWidth": "0"}

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


def repeater(key, row, path=None, styles=None, **kwargs):
	"""A block that renders its one child once per row of `key`.

	The rows come out as children of this block, not of its parent, so a grid or a
	flex row has to be styled *here*. Styled on the parent instead, every row lands in
	the parent's first cell: the repeater itself is that cell.
	"""
	node = block("div", path=path, styles=styles, isRepeaterBlock=True, children=[row], **kwargs)
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


def card(title, subtitle_key, body, action=None):
	"""A titled panel with a subtitle from data. Every portal page is built of these.

	`action` is the one thing the card offers to press, sat at the end of its title
	row. Without one the head is the title and its subtitle, as it always was.
	"""
	titles = [
		block("h2", styles=CARD_TITLE_STYLES, html=title),
		bound("div", subtitle_key, styles=CARD_SUB_STYLES),
	]
	head = (
		block("div", styles=CARD_HEAD_STYLES, children=titles)
		if action is None
		else block(
			"div",
			styles=CARD_HEAD_ROW_STYLES,
			children=[block("div", styles=CARD_TITLES_STYLES, children=titles), action],
		)
	)

	return block("section", styles=CARD_STYLES, children=[head, body])


def reveal_button(label, name, styles=None):
	"""A button that brings out the panel marked with `name`, and hides itself doing it.

	The pair is wired by name in the shared client script, so a page that wants a
	section kept back until it is asked for needs no JavaScript of its own.
	"""
	return block(
		"button",
		styles=styles or GHOST_BTN_STYLES,
		html=label,
		attributes={"type": "button", "data-reveals": name},
	)


# The shape of a record list: one wide column saying what the row is, then two narrow
# ones. The headings and the rows read it from here, so they cannot drift apart.
RECORD_COLUMNS = (COL_MAIN_STYLES, COL_STATUS_STYLES, COL_AMT_STYLES)


def record_table(labels, columns, key, url_key="url"):
	"""A heading row and one row per record, each row linking to its own page.

	`columns` carries the blocks for each column of a row, in the order of `labels`.
	Widths come from RECORD_COLUMNS, so a heading always sits over its own column.
	The headings go with the rows: a table of nothing is a worse empty state than the
	card's own subtitle, which already says there is nothing to list.
	"""
	head = block(
		"div",
		styles=THEAD_STYLES,
		children=[
			block("span", styles={**RECORD_COLUMNS[index], **THEAD_LABEL_STYLES}, html=label)
			for index, label in enumerate(labels)
		],
	)
	head["visibilityCondition"] = key

	row = linked(
		url_key,
		styles={**ROW_STYLES, "color": "inherit"},
		children=[
			block("div", styles=RECORD_COLUMNS[index], children=children)
			for index, children in enumerate(columns)
		],
	)

	return block("div", children=[head, repeater(key, row)])


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


def download_link(url_key, label_key):
	"""A button-styled link whose destination and wording both come from the data.

	Two bindings need two nodes: a block carries one dataKey, so the anchor binds its
	href and the span inside it binds the label. The href arrives from the data rather
	than being fixed at build time, so the link carries whichever period or year the
	page is currently showing.
	"""
	anchor = block(
		"a",
		styles={**BTN_STYLES, "textDecoration": "none", "width": "fit-content"},
		children=[bound("span", label_key)],
		attributes={"href": "#"},
	)

	return block(
		"div", styles={"padding": "0 12px 12px"}, children=[bind(anchor, url_key, property="href", type="attribute")]
	)


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
	"padding": "0 20px 64px",
	"gap": "0",
	"background": GRAY_50,
}
PUBLIC_COLUMN_STYLES = {**COLUMN, "width": "100%", "maxWidth": "720px", "gap": "18px"}

FIELD_STYLES = {**COLUMN, "gap": "6px", "padding": "8px 12px"}
LABEL_STYLES = {"fontSize": "13px", "fontWeight": "500", "color": GRAY_700}
INPUT_STYLES = {
	"fontFamily": "inherit",
	"fontSize": "14px",
	"padding": "10px 12px",
	"borderRadius": "var(--brand-radius,10px)",
	"border": BORDER,
	"background": WHITE,
	"color": GRAY_900,
	"width": "100%",
	"boxSizing": "border-box",
	"hover:borderColor": GRAY_500,
}
# An answer already given, shown back rather than asked for twice.
ECHO_INPUT_STYLES = {**INPUT_STYLES, "background": GRAY_100, "color": GRAY_700, "hover:borderColor": GRAY_200}
ECHO_NOTE_STYLES = {**ROW_FLEX, "gap": "5px", "fontSize": "12px", "fontWeight": "500", "color": GREEN_700}
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


def label_block(label, required=True):
	"""One field label, carrying the asterisk people look for.

	Required-ness was only in the note above the form before, so the one field holding
	a visitor up was whichever they had skipped, and the form would not say which.
	"""
	mark = f' <span style="color: {RED_600}">*</span>' if required else ""

	return block("label", styles=LABEL_STYLES, html=f"{label}{mark}")


def field(label, name, input_type="text", placeholder="", required=True):
	"""One labelled input. The name is what the client script posts."""
	attributes = {"name": name, "type": input_type, "placeholder": placeholder or label}
	if required:
		attributes["required"] = "required"

	return block(
		"div",
		styles=FIELD_STYLES,
		children=[
			label_block(label, required),
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
			label_block(label),
			block(
				"select",
				styles=INPUT_STYLES,
				attributes={"name": name, "required": "required"},
				children=[repeater(options_key, option)],
			),
		],
	)


def hidden_input(name, value=""):
	"""An answer given on an earlier screen, carried to the step that posts it.

	The screens are separate panels of one page, so a choice made on the second lands
	here and travels with the form on the fifth. Nothing reads these but the script.
	"""
	return block("input", attributes={"type": "hidden", "name": name, "value": value})


def echo_field(label, note, mark):
	"""A detail the visitor has already given, shown back to them, not asked again.

	No name and disabled, so it is never posted: the value the server trusts is the
	one it verified, and a second copy in the form could only disagree with it.
	"""
	return block(
		"div",
		styles=FIELD_STYLES,
		children=[
			label_block(label, required=False),
			block(
				"input",
				styles=ECHO_INPUT_STYLES,
				attributes={"type": "text", "disabled": "disabled", mark: "1"},
			),
			block(
				"div",
				styles=ECHO_NOTE_STYLES,
				html=f"{ICON_CHECK}<span>{note}</span>",
				attributes={"data-echo-note": "1"},
			),
		],
	)


# --- the top band -------------------------------------------------------------------
#
# The public pages used to open on a hero the height of the screen, which pushed the
# first question below the fold. The band is now only the brand and the two ways off
# the page, and it follows the visitor down so both stay reachable. /apply carries its
# promise on its own first screen; /track has nothing but a form, so it keeps a heading.

BAND_STYLES = {
	**COLUMN,
	"width": "100%",
	"alignItems": "center",
	"background": WHITE,
	"borderBottom": BORDER,
	"padding": "0 20px",
	"marginBottom": "28px",
	"position": "sticky",
	"top": "0",
	"zIndex": "20",
}
BAND_COLUMN_STYLES = {**COLUMN, "width": "100%", "maxWidth": "720px", "gap": "14px"}
TOPBAR_STYLES = {**ROW_FLEX, "gap": "10px", "padding": "13px 0", "width": "100%"}
TOPBAR_LINKS_STYLES = {**ROW_FLEX, "marginLeft": "auto", "gap": "14px"}
TOPBAR_LINK_STYLES = {
	"fontSize": "13px",
	"fontWeight": "500",
	"color": GRAY_700,
	"textDecoration": "none",
	"hover:color": GRAY_950,
}
# The way back in, for a visitor who has applied before. A pill rather than a third
# link, because it is the only thing in the bar anybody arrives looking for.
PILL_LINK_STYLES = {
	**ROW_FLEX,
	"gap": "7px",
	"padding": "7px 14px",
	"borderRadius": "999px",
	"border": BORDER,
	"background": WHITE,
	"fontSize": "13px",
	"fontWeight": "500",
	"color": GRAY_900,
	"textDecoration": "none",
	"whiteSpace": "nowrap",
	"hover:borderColor": GRAY_500,
}

HERO_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "30px",
	"lineHeight": "1.15",
	"fontWeight": "600",
	"color": GRAY_950,
	"letterSpacing": "-0.02em",
	"maxWidth": "20ch",
}
HERO_TITLE_MOBILE_STYLES = {"fontSize": "24px"}
HERO_INTRO_STYLES = {
	"margin": "0",
	"fontSize": "15px",
	"lineHeight": "1.55",
	"color": GRAY_700,
	"maxWidth": "56ch",
}

# The research was unanimous that the "no credit score impact" promise belongs next to
# the first field, not in the small print. Three of these sit under the opening card.
TRUST_ROW_STYLES = {"display": "flex", "flexWrap": "wrap", "gap": "18px"}
TRUST_ITEM_STYLES = {**ROW_FLEX, "gap": "7px"}
TRUST_TICK_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"width": "16px",
	"height": "16px",
	"flexShrink": "0",
	"borderRadius": "999px",
	"background": GREEN_100,
	"color": GREEN_700,
	"fontSize": "10px",
	"fontWeight": "600",
}
TRUST_TEXT_STYLES = {"fontSize": "13px", "color": GRAY_700}


def trust_row(key):
	"""The three promises, in a row. One line each, no small print."""
	item = block(
		"div",
		styles=TRUST_ITEM_STYLES,
		children=[
			block("span", styles=TRUST_TICK_STYLES, html="&#10003;"),
			bound("span", "label", styles=TRUST_TEXT_STYLES),
		],
	)

	return repeater(key, item, styles=TRUST_ROW_STYLES)


# --- the opening screen -------------------------------------------------------------
#
# A form is work to be done; an invitation is not. The first screen asks for nothing,
# says how long the rest takes, and offers one button.

START_CARD_STYLES = {
	**ROW_FLEX,
	"gap": "24px",
	"flexWrap": "wrap",
	"justifyContent": "space-between",
	"padding": "30px 32px",
	"border": BORDER,
	"borderRadius": "var(--brand-radius,14px)",
	"background": f"linear-gradient(150deg, {WHITE} 0%, {GRAY_50} 60%, {GREEN_100} 220%)",
	"boxShadow": ACTIVE_SHADOW,
}
START_CARD_MOBILE_STYLES = {"padding": "24px 20px"}
START_COPY_STYLES = {**COLUMN, "gap": "6px", "minWidth": "0"}
START_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "24px",
	"fontWeight": "600",
	"letterSpacing": "-0.01em",
	"color": GRAY_950,
}
START_NOTE_STYLES = {"margin": "0", "fontSize": "14px", "color": GRAY_700}

BENEFIT_ROW_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
	"gap": "18px",
	"padding": "2px 2px 0",
}
BENEFIT_ROW_TABLET_STYLES = {"gridTemplateColumns": "minmax(0, 1fr)"}
BENEFIT_ITEM_STYLES = {**COLUMN, "gap": "5px"}
BENEFIT_HEAD_STYLES = {**ROW_FLEX, "gap": "9px"}
BENEFIT_NUMBER_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"width": "20px",
	"height": "20px",
	"flexShrink": "0",
	"borderRadius": "999px",
	"background": "var(--brand-primary,#171717)",
	"color": "var(--brand-primary-ink,#ffffff)",
	"fontSize": "11px",
	"fontWeight": "600",
}
BENEFIT_TITLE_STYLES = {"fontSize": "14px", "fontWeight": "600", "color": GRAY_950}
BENEFIT_NOTE_STYLES = {"margin": "0", "fontSize": "13px", "color": GRAY_600, "lineHeight": "1.5"}


def benefits(key):
	"""Three numbered reasons to start, under the opening card."""
	item = block(
		"div",
		styles=BENEFIT_ITEM_STYLES,
		children=[
			block(
				"div",
				styles=BENEFIT_HEAD_STYLES,
				children=[
					bound("span", "step", styles=BENEFIT_NUMBER_STYLES),
					bound("span", "title", styles=BENEFIT_TITLE_STYLES),
				],
			),
			bound("p", "note", styles=BENEFIT_NOTE_STYLES),
		],
	)

	return repeater(key, item, styles=BENEFIT_ROW_STYLES, tabletStyles=BENEFIT_ROW_TABLET_STYLES)


# --- the progress bar ---------------------------------------------------------------
#
# One question per screen only works if the visitor can see how much is left, so the
# bar names the step they are on and counts the ones still to come. The script moves
# it; the styles here only describe it.

PROGRESS_STYLES = {**COLUMN, "gap": "8px", "width": "100%", "padding": "0 2px"}
PROGRESS_HEAD_STYLES = {**ROW_FLEX, "justifyContent": "space-between", "gap": "10px"}
PROGRESS_NAME_STYLES = {"fontSize": "13px", "fontWeight": "600", "color": GRAY_950}
PROGRESS_COUNT_STYLES = {**TABULAR, "fontSize": "12px", "fontWeight": "500", "color": GRAY_600}
PROGRESS_TRACK_STYLES = {
	"width": "100%",
	"height": "4px",
	"borderRadius": "999px",
	"background": GRAY_200,
	"overflow": "hidden",
}
PROGRESS_FILL_STYLES = {
	"width": "0%",
	"height": "4px",
	"borderRadius": "999px",
	"background": "var(--brand-primary,#171717)",
	"transition": "width 240ms ease",
}


def progress_bar(steps):
	"""How far along, and how far to go. `data-progress` is how many steps there are."""
	return block(
		"div",
		styles=PROGRESS_STYLES,
		attributes={"data-progress": str(steps), "hidden": "hidden"},
		children=[
			block(
				"div",
				styles=PROGRESS_HEAD_STYLES,
				children=[
					block("span", styles=PROGRESS_NAME_STYLES, attributes={"data-progress-name": "1"}),
					block("span", styles=PROGRESS_COUNT_STYLES, attributes={"data-progress-count": "1"}),
				],
			),
			block(
				"div",
				styles=PROGRESS_TRACK_STYLES,
				children=[
					block("div", styles=PROGRESS_FILL_STYLES, attributes={"data-progress-fill": "1"})
				],
			),
		],
	)


# --- panels, fields and buttons -----------------------------------------------------

WIZARD_STYLES = {**COLUMN, "gap": "18px"}
PANEL_STYLES = {
	**COLUMN,
	"background": WHITE,
	"border": BORDER,
	"borderRadius": "var(--brand-radius,14px)",
	"boxShadow": ACTIVE_SHADOW,
	"overflow": "hidden",
}
# The opening screen is not a card: it is the page's own invitation, and a border
# around it would make it look like the first of several things to fill in.
OPENING_STYLES = {**COLUMN, "gap": "20px"}
PANEL_HEAD_STYLES = {**COLUMN, "gap": "6px", "padding": "26px 28px 0"}
PANEL_STEP_STYLES = {
	"fontSize": "11px",
	"fontWeight": "600",
	"letterSpacing": "0.06em",
	"textTransform": "uppercase",
	"color": GRAY_500,
}
PANEL_TITLE_STYLES = {"margin": "0", "fontSize": "18px", "fontWeight": "600", "color": GRAY_950}
PANEL_SUB_STYLES = {"margin": "0", "fontSize": "13px", "color": GRAY_700, "lineHeight": "1.5"}

# One question per screen, asked at the size of the only thing being asked.
QUESTION_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "26px",
	"lineHeight": "1.2",
	"fontWeight": "600",
	"letterSpacing": "-0.02em",
	"color": GRAY_950,
}
QUESTION_TITLE_MOBILE_STYLES = {"fontSize": "21px"}
QUESTION_SUB_STYLES = {"margin": "0", "fontSize": "14px", "color": GRAY_600, "lineHeight": "1.5"}

# What was answered two screens ago, on the screen that posts it, so a visitor does
# not have to walk back to remind themselves what they picked.
PICKED_ROW_STYLES = {"display": "flex", "flexWrap": "wrap", "gap": "8px", "padding": "14px 28px 0"}
PICKED_STYLES = {
	**ROW_FLEX,
	"gap": "6px",
	"padding": "5px 10px",
	"borderRadius": "999px",
	"background": GRAY_100,
	"fontSize": "12px",
	"fontWeight": "500",
	"color": GRAY_700,
}

PANEL_BODY_STYLES = {**COLUMN, "gap": "2px", "padding": "18px 16px 4px"}

# Two columns on a laptop, one on a phone. Seven stacked boxes was the single worst
# thing about the old page.
FIELD_GRID_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
	"gap": "6px 12px",
	"padding": "10px 16px 4px",
}
FIELD_GRID_TABLET_STYLES = {"gridTemplateColumns": "minmax(0, 1fr)"}
FIELD_WIDE_STYLES = {"gridColumn": "1 / -1"}

# A long form reads as shorter in named groups than as one run of boxes.
FORM_SECTION_STYLES = {
	"gridColumn": "1 / -1",
	"margin": "14px 0 0",
	"padding": "0 12px",
	"fontSize": "11px",
	"fontWeight": "600",
	"letterSpacing": "0.06em",
	"textTransform": "uppercase",
	"color": GRAY_500,
}


def form_section(label):
	"""A heading inside the field grid, spanning both of its columns."""
	return block("div", styles=FORM_SECTION_STYLES, html=label)


# The wizard's own buttons. The desk pages' BTN_STYLES is a toolbar button; these are
# the one thing to press on the screen, and they are sized to say so.
WIZARD_BTN_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"gap": "7px",
	"padding": "11px 20px",
	"borderRadius": "var(--brand-radius,10px)",
	"border": "1px solid transparent",
	"background": "var(--brand-primary,#171717)",
	"color": "var(--brand-primary-ink,#ffffff)",
	"fontFamily": "inherit",
	"fontSize": "14px",
	"fontWeight": "600",
	"cursor": "pointer",
	"whiteSpace": "nowrap",
	"textDecoration": "none",
	"hover:filter": "brightness(1.35)",
}
WIZARD_GHOST_STYLES = {
	**WIZARD_BTN_STYLES,
	"background": WHITE,
	"border": BORDER,
	"color": GRAY_900,
	"fontWeight": "500",
	"hover:filter": "none",
	"hover:borderColor": GRAY_500,
}
GHOST_BTN_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"gap": "6px",
	"padding": "8px 14px",
	"borderRadius": "var(--brand-radius,8px)",
	"border": BORDER,
	"background": WHITE,
	"color": GRAY_900,
	"fontFamily": "inherit",
	"fontSize": "13px",
	"fontWeight": "500",
	"cursor": "pointer",
}
# "Send it again" is not a way forward, so it does not look like one.
LINK_BTN_STYLES = {
	"padding": "0",
	"border": "0",
	"background": "transparent",
	"color": GRAY_700,
	"fontFamily": "inherit",
	"fontSize": "13px",
	"fontWeight": "500",
	"textDecoration": "underline",
	"cursor": "pointer",
}

NAV_ROW_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"justifyContent": "space-between",
	"padding": "18px 28px",
	"marginTop": "20px",
	"borderTop": BORDER,
	"background": GRAY_50,
}
NAV_END_STYLES = {**ROW_FLEX, "gap": "10px", "marginLeft": "auto"}
QUIET_NOTE_STYLES = {"fontSize": "12px", "color": GRAY_600, "lineHeight": "1.5"}


def wizard_button(label, styles, chevron=None, leading=False, attributes=None):
	"""A button whose label is its own element.

	The script swaps the label for "Working..." while a request is in flight, and a
	chevron beside a bare text node would be swapped away with it.
	"""
	parts = [f'<span data-label="1">{label}</span>']
	if chevron:
		parts.insert(0 if leading else 1, chevron)

	return block(
		"button",
		styles=styles,
		html="".join(parts),
		attributes={"type": "button", **(attributes or {})},
	)


def nav_row(back=None, forward=()):
	"""The way back and the way on, at the foot of one screen.

	Back sits left and on sits right even when there is no back, because a button that
	moves about between screens is a button that gets missed.
	"""
	return block(
		"div",
		styles=NAV_ROW_STYLES,
		children=[
			back or block("span", styles={"display": "block"}),
			block("div", styles=NAV_END_STYLES, children=list(forward)),
		],
	)


# --- the choice tiles ---------------------------------------------------------------
#
# A select hides its options until it is opened, and the two questions that decide the
# whole form -- who is borrowing, and what for -- are worth a screen each. These are
# buttons rather than radios: at this size the dot is the smallest part of the control,
# and only a script can restyle the whole of the chosen one.

CHOICE_GRID_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
	"gap": "12px",
	"padding": "22px 28px 6px",
}
CHOICE_GRID_TABLET_STYLES = {"gridTemplateColumns": "minmax(0, 1fr)"}
TILE_STYLES = {
	**ROW_FLEX,
	"gap": "14px",
	"width": "100%",
	"padding": "16px",
	"boxSizing": "border-box",
	"textAlign": "left",
	"background": WHITE,
	"border": BORDER,
	"borderRadius": "var(--brand-radius,12px)",
	"fontFamily": "inherit",
	"color": GRAY_900,
	"cursor": "pointer",
	"hover:borderColor": GRAY_500,
}
TILE_ICON_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"width": "40px",
	"height": "40px",
	"flexShrink": "0",
	"borderRadius": "10px",
	"background": GRAY_100,
	"color": GRAY_700,
}
TILE_BODY_STYLES = {
	**COLUMN,
	"gap": "3px",
	"flex": "1 1 auto",
	"minWidth": "0",
	"alignItems": "flex-start",
}
TILE_LABEL_STYLES = {"fontSize": "15px", "fontWeight": "600", "color": GRAY_950}
TILE_NOTE_STYLES = {"fontSize": "13px", "color": GRAY_600, "lineHeight": "1.45"}
TILE_META_STYLES = {**ROW_FLEX, "gap": "6px", "flexWrap": "wrap", "fontSize": "12px", "color": GRAY_600}
TILE_RADIO_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"width": "20px",
	"height": "20px",
	"flexShrink": "0",
	"borderRadius": "999px",
	"border": f"1px solid {GRAY_500}",
	"background": WHITE,
	"color": WHITE,
}


def tile(icon, body, value=None, value_key=None):
	"""One answer, the size of the question. `data-value` is what the script posts."""
	attributes = {"type": "button", "data-tile": "1", "role": "radio", "aria-checked": "false"}
	if value:
		attributes["data-value"] = value

	node = block(
		"button",
		styles=TILE_STYLES,
		attributes=attributes,
		children=[
			block("span", styles=TILE_ICON_STYLES, html=icon, attributes={"data-tile-icon": "1"}),
			block("span", styles=TILE_BODY_STYLES, children=list(body)),
			block("span", styles=TILE_RADIO_STYLES, html=ICON_CHECK, attributes={"data-tile-radio": "1"}),
		],
	)

	# A repeated tile carries its own value, one row at a time.
	return bind(node, value_key, property="data-value", type="attribute") if value_key else node


def choice_tile(value, icon, label, note):
	"""A tile whose wording is fixed, for a question with fixed answers."""
	return tile(
		icon,
		[
			block("span", styles=TILE_LABEL_STYLES, html=label, attributes={"data-tile-label": "1"}),
			block("span", styles=TILE_NOTE_STYLES, html=note),
		],
		value=value,
	)


def tile_group(name, label, tiles):
	"""The tiles for one question, and the field name their answer lands in."""
	return block(
		"div",
		styles=CHOICE_GRID_STYLES,
		tabletStyles=CHOICE_GRID_TABLET_STYLES,
		attributes={"data-choice": name, "role": "radiogroup", "aria-label": label},
		children=list(tiles),
	)


def product_tiles(key, name):
	"""One tile per Loan Product, with the rate and the ceiling on it.

	The products were a list under the form, which reads as fine print. They are the
	choice the rest of the form depends on, so they are the screen that asks for it.
	"""
	rate = block(
		"span",
		styles=TILE_META_STYLES,
		children=[
			bound(
				"span",
				"rate",
				styles={**TABULAR, "fontSize": "14px", "fontWeight": "600", "color": GRAY_950},
			),
			bound("span", "rate_note"),
		],
	)
	strong = {"fontWeight": "500", "color": GRAY_700}
	ceiling = block(
		"span",
		styles=TILE_META_STYLES,
		children=[
			block("span", html="Up to"),
			bound("span", "ceiling", styles={**TABULAR, **strong}),
			block("span", html="&middot;"),
			bound("span", "kind", styles=strong),
		],
	)
	row = tile(
		ICON_MONEY,
		[
			bound("span", "label", styles=TILE_LABEL_STYLES, attributes={"data-tile-label": "1"}),
			rate,
			ceiling,
		],
		value_key="value",
	)

	return repeater(
		key,
		row,
		styles=CHOICE_GRID_STYLES,
		tabletStyles=CHOICE_GRID_TABLET_STYLES,
		attributes={"data-choice": name, "role": "radiogroup", "aria-label": "Loan product"},
	)


# --- the code boxes -----------------------------------------------------------------
#
# Six separate boxes rather than one input. It is the shape people expect from every
# other app that sends a code, and it makes a wrong length obvious before submitting.

CODE_ROW_STYLES = {**ROW_FLEX, "gap": "8px", "flexWrap": "wrap", "padding": "10px 28px 4px"}
CODE_BOX_STYLES = {
	**TABULAR,
	"width": "44px",
	"height": "50px",
	"textAlign": "center",
	"fontFamily": "inherit",
	"fontSize": "19px",
	"fontWeight": "600",
	"borderRadius": "var(--brand-radius,8px)",
	"border": BORDER,
	"background": WHITE,
	"color": GRAY_950,
	"boxSizing": "border-box",
}


def code_boxes(count=6):
	"""`data-code` marks the group; the script joins the digits and moves focus."""
	return block(
		"div",
		styles=CODE_ROW_STYLES,
		attributes={"data-code": "1"},
		children=[
			block(
				"input",
				styles=CODE_BOX_STYLES,
				attributes={
					"type": "text",
					"inputmode": "numeric",
					"maxlength": "1",
					# A space, not nothing: the filled-box style keys off
					# :not(:placeholder-shown), which never matches without one.
					"placeholder": " ",
					"autocomplete": "one-time-code" if index == 0 else "off",
					"aria-label": f"Digit {index + 1}",
				},
			)
			for index in range(count)
		],
	)


# --- the offer ----------------------------------------------------------------------
#
# The old page printed the offer as unstyled lines of text under the form. An offer is
# the one thing on this page the visitor came for, so it gets the largest number.

OFFER_STYLES = {
	**COLUMN,
	"gap": "0",
	"border": f"1px solid {GREEN_700}",
	"borderRadius": "var(--brand-radius,12px)",
	"overflow": "hidden",
	"background": WHITE,
}
OFFER_HEAD_STYLES = {**COLUMN, "gap": "3px", "padding": "18px 20px", "background": GREEN_100}
OFFER_HEADLINE_STYLES = {"fontSize": "17px", "fontWeight": "600", "color": GREEN_700}
OFFER_MESSAGE_STYLES = {"fontSize": "13px", "color": GRAY_700, "lineHeight": "1.5"}
OFFER_GRID_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
	"borderTop": f"1px solid {GREEN_100}",
}
OFFER_CELL_STYLES = {**COLUMN, "gap": "4px", "padding": "16px 20px"}
OFFER_LABEL_STYLES = {"fontSize": "12px", "color": GRAY_600}
OFFER_VALUE_STYLES = {**TABULAR, "fontSize": "20px", "fontWeight": "600", "color": GRAY_950}
OFFER_FOOT_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"flexWrap": "wrap",
	"padding": "14px 20px",
	"borderTop": BORDER,
	"background": GRAY_50,
}
REFERENCE_STYLES = {**TABULAR, "fontSize": "13px", "color": GRAY_700}


# --- the tracker timeline -----------------------------------------------------------

TIMELINE_STYLES = {**COLUMN, "gap": "0", "padding": "4px 20px 4px"}
TIMELINE_ROW_STYLES = {"display": "flex", "gap": "12px", "alignItems": "flex-start"}
TIMELINE_MARK_STYLES = {**COLUMN, "alignItems": "center", "gap": "0", "flexShrink": "0"}
TIMELINE_DOT_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"width": "20px",
	"height": "20px",
	"marginTop": "10px",
	"borderRadius": "999px",
	"fontSize": "10px",
	"fontWeight": "700",
}
TIMELINE_STEM_STYLES = {"width": "1px", "flex": "1 1 auto", "minHeight": "18px", "background": GRAY_200}
TIMELINE_BODY_STYLES = {**COLUMN, "gap": "2px", "padding": "8px 0 14px"}
TIMELINE_TITLE_STYLES = {"fontSize": "14px", "fontWeight": "500", "color": GRAY_950}
TIMELINE_NOTE_STYLES = {"fontSize": "13px", "color": GRAY_600, "lineHeight": "1.5"}


def timeline_shell():
	"""An empty vertical track plus the row the script clones per step.

	A Builder repeater renders from the page data script, which runs once on the
	server. The tracker's steps only exist after the visitor posts a reference number,
	so this cannot be a repeater. Rendering the row here anyway keeps its styling in
	the theme with everything else, and leaves the script holding text alone.
	"""
	row = block(
		"div",
		styles=TIMELINE_ROW_STYLES,
		attributes={"data-step-row": "1", "hidden": "hidden"},
		children=[
			block(
				"div",
				styles=TIMELINE_MARK_STYLES,
				children=[
					block("span", styles=TIMELINE_DOT_STYLES, attributes={"data-step-mark": "1"}),
					block("span", styles=TIMELINE_STEM_STYLES, attributes={"data-step-stem": "1"}),
				],
			),
			block(
				"div",
				styles=TIMELINE_BODY_STYLES,
				children=[
					block("div", styles=TIMELINE_TITLE_STYLES, attributes={"data-step-title": "1"}),
					block("div", styles=TIMELINE_NOTE_STYLES, attributes={"data-step-note": "1"}),
				],
			),
		],
	)

	return block("div", styles=TIMELINE_STYLES, attributes={"data-timeline": "1"}, children=[row])


def offer_card(action_href="/login"):
	"""The result panel: a headline, a row of large figures, and what to do next.

	Filled by the client script for the same reason as timeline_shell. The figure cell
	is cloned per row, so an offer with one number and an offer with three both look
	deliberate.
	"""
	cell = block(
		"div",
		styles=OFFER_CELL_STYLES,
		attributes={"data-offer-cell": "1", "hidden": "hidden"},
		children=[
			block("div", styles=OFFER_LABEL_STYLES, attributes={"data-offer-label": "1"}),
			block("div", styles=OFFER_VALUE_STYLES, attributes={"data-offer-value": "1"}),
		],
	)

	return block(
		"div",
		styles=OFFER_STYLES,
		attributes={"data-offer": "1", "hidden": "hidden"},
		children=[
			block(
				"div",
				styles=OFFER_HEAD_STYLES,
				children=[
					block("div", styles=OFFER_HEADLINE_STYLES, attributes={"data-offer-headline": "1"}),
					block("div", styles=OFFER_MESSAGE_STYLES, attributes={"data-offer-message": "1"}),
				],
			),
			block("div", styles=OFFER_GRID_STYLES, attributes={"data-offer-grid": "1"}, children=[cell]),
			block(
				"div",
				styles=OFFER_FOOT_STYLES,
				children=[
					block("span", styles=REFERENCE_STYLES, attributes={"data-offer-reference": "1"}),
					block(
						"a",
						styles={**BTN_STYLES, "marginLeft": "auto", "textDecoration": "none"},
						attributes={"href": action_href, "data-offer-action": "1", "hidden": "hidden"},
					),
				],
			),
		],
	)


# --- the frame ----------------------------------------------------------------------


def bound_field(label, name, value_key, input_type="text", required=False):
	"""A labelled input that opens with whatever is already on record.

	The value arrives as a bound attribute rather than as text, so the borrower sees
	their current details in the boxes and corrects the one that is wrong instead of
	retyping all of them.
	"""
	attributes = {"name": name, "type": input_type}
	if required:
		attributes["required"] = "required"

	control = bind(
		block("input", styles=INPUT_STYLES, attributes=attributes), value_key, property="value", type="attribute"
	)

	return block(
		"div",
		styles=FIELD_STYLES,
		children=[label_block(label, required), control],
	)


def hidden_field(name, value_key):
	"""A value the form must post but the borrower does not type.

	Bound rather than fixed at build time, so the form always names whichever record
	the page is currently showing.
	"""
	return bind(
		block("input", styles={"display": "none"}, attributes={"name": name, "type": "hidden"}),
		value_key,
		property="value",
		type="attribute",
	)


def switch_links(key):
	"""One link per record, for a borrower who holds more than one.

	A select would need pre-selecting from data, which a Builder page cannot do
	without shipping the page's data to the script. Links carry the choice in the URL
	instead, and the server decides what is selected.
	"""
	anchor = linked(
		"url",
		styles={**GHOST_BTN_STYLES, "textDecoration": "none"},
		children=[bound("span", "label")],
	)

	return block(
		"div",
		styles={"display": "flex", "flexWrap": "wrap", "gap": "8px", "padding": "8px 12px 12px"},
		children=[repeater(key, anchor)],
	)


def file_field(label, name, accept, note=None):
	"""One file input. The accept list is a hint to the browser, never the check."""
	children = [
		label_block(label),
		block(
			"input",
			styles={**INPUT_STYLES, "padding": "7px 8px"},
			attributes={"name": name, "type": "file", "accept": accept, "required": "required"},
		),
	]
	if note:
		children.append(block("div", styles=QUIET_NOTE_STYLES, html=note))

	return block("div", styles=FIELD_STYLES, children=children)


def choice_field(label, name, choices, required=False):
	"""A select whose options are fixed in code rather than fetched.

	Loan Lead.employment_type is a Select with two values. Offering them as a text box
	would let a visitor type something the backend then silently drops, so the page
	offers exactly what the field accepts.
	"""
	blank = block("option", styles={}, html="", attributes={"value": ""})
	options = [blank] + [
		block("option", styles={}, html=choice, attributes={"value": choice}) for choice in choices
	]

	attributes = {"name": name}
	if required:
		attributes["required"] = "required"

	return block(
		"div",
		styles=FIELD_STYLES,
		children=[
			label_block(label, required),
			block("select", styles=INPUT_STYLES, attributes=attributes, children=options),
		],
	)


def topbar(links):
	"""The brand, and the ways off this page.

	The last link is the way back in, which is the only thing anybody arrives in this
	bar looking for, so it is a pill rather than the third of three identical links.
	"""
	children = [
		block("span", styles=MARK_STYLES, html=ICON_BRAND),
		bound(
			"span", "brand_name", styles={"fontSize": "14px", "fontWeight": "500", "color": BLACK}
		),
	]

	if links:
		*plain, (last_label, last_href) = links
		children.append(
			block(
				"div",
				styles=TOPBAR_LINKS_STYLES,
				children=[
					*(
						block("a", styles=TOPBAR_LINK_STYLES, html=label, attributes={"href": href})
						for label, href in plain
					),
					block(
						"a",
						styles=PILL_LINK_STYLES,
						html=f"{ICON_PERSON}<span>{last_label}</span>",
						attributes={"href": last_href},
					),
				],
			)
		)

	return block("div", styles=TOPBAR_STYLES, children=children)


def public_frame(children, heading_key=None, intro_key=None, trust_key=None, links=()):
	"""The public shell: a white band with the brand in it, then the page's content.

	A page says here what it is only if it has nowhere better. /apply carries its
	promise on its own first screen, so it passes no heading and the band stays a bar;
	/track is a single form and keeps a heading above it.
	"""
	band = [topbar(links)]
	if heading_key:
		band.append(
			block(
				"h1",
				styles=HERO_TITLE_STYLES,
				mobileStyles=HERO_TITLE_MOBILE_STYLES,
				children=[bound("span", heading_key)],
			)
		)
	if intro_key:
		band.append(bound("p", intro_key, styles=HERO_INTRO_STYLES))
	if trust_key:
		band.append(trust_row(trust_key))

	styles = BAND_STYLES if len(band) == 1 else {**BAND_STYLES, "paddingBottom": "32px"}

	return block(
		"div",
		styles=PUBLIC_PAGE_STYLES,
		children=[
			block(
				"div",
				styles=styles,
				children=[block("div", styles=BAND_COLUMN_STYLES, children=band)],
			),
			block("div", styles=PUBLIC_COLUMN_STYLES, children=list(children)),
		],
	)
