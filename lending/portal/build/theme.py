# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Shared block helpers and styles for the borrower portal's Builder pages.

Every visual rule lives on its own block, in baseStyles, because that is the only
styling the Builder canvas reads. The canvas applies baseStyles inline to each element
and never loads the page head_html, so a page styled through a head_html stylesheet
renders as unstyled text there and cannot be arranged by hand. Rules that CSS would
share through one class are therefore repeated per block. That repetition is the price
of a canvas that shows the real page.

Brand colours, fonts, radii and the size scale stay in Builder Token records, which
the canvas does serve as custom properties, so a bank restyles without touching this
file. It does that from the Borrower Portal section of Lending Settings, which writes
the tokens on save -- see upsert_tokens below. Every size of text names a token and
carries the shipped value as its fallback, so the scale is changed in one place rather
than at each block that names a size. The three exceptions are marked where they stand:
a glyph centred in a circle of a fixed width cannot grow with the rest. The palette holds the Espresso tokens from the
installed frappe source, inlined as literals because :root custom properties declared in
head_html do not reach the canvas.
"""

import hashlib

from builder.builder.doctype.builder_token.builder_token import clear_builder_token_cache

import frappe

# What the portal carries brand in. A lender sets two of them on Lending Settings -- a
# colour and an accent -- and brand_overrides() derives the rest, because nobody should
# be asked to pick the text colour for their own button. These values are
# the default for a site that has configured nothing.
BRAND_TOKENS = [
	{"token_name": "brand-primary", "type": "Color", "value": "#171717", "dark_value": "#f8f8f8"},
	{"token_name": "brand-primary-ink", "type": "Color", "value": "#ffffff", "dark_value": "#171717"},
	{"token_name": "brand-mark", "type": "Color", "value": "#2bb24c", "dark_value": "#2fbe6a"},
	{"token_name": "brand-mark-ink", "type": "Color", "value": "#ffffff", "dark_value": "#171717"},
	# The accent at two other lightnesses: a tint to sit behind it, and a deepened
	# version of it to write on that tint.
	{"token_name": "brand-mark-soft", "type": "Color", "value": "#e4faeb", "dark_value": "#e4faeb"},
	{"token_name": "brand-mark-deep", "type": "Color", "value": "#14804d", "dark_value": "#14804d"},
	{"token_name": "brand-radius", "type": "Dimension", "value": "8px"},
	{"token_name": "brand-font", "type": "Font", "value": "InterVariable"},
]

# How the portal is set, as opposed to what it is branded. Two families rather than one,
# because they answer to different people: a lender picks the brand-* values, and the
# portal-* values are the portal's own size scale, which nobody configures. The prefix
# also keeps them out of the way of whatever tokens a site's own Builder pages already
# define, since a Builder Token emits --<document name> into one global namespace shared
# with the rest of the site.
#
# Nine tokens, because they are what a page is made of: six sizes of text, and the three
# distances that decide whether a page feels like a bank or like an admin tool. They are
# named rather than written into the blocks so that the scale moves as one: a page whose
# sizes were nine separate numbers would read as nine unrelated pages.
#
# Every size is a step of the desk's own scale, read off the Espresso typography tokens
# in frappe/public/css/espresso/typography.css, so that a borrower who has also seen the
# desk reads the two at one size. The portal sets sub-headings in --text-base and body
# in --text-sm, which is where the desk itself sets a section heading and a row. The
# names below stay portal-* because the canvas cannot reach the desk's variables, but
# the values are the desk's, not a scale of our own:
#
#     xs 11px  --text-2xs    labels, column heads, badges
#     sm 12px  --text-xs     text held quiet, the size of a desk timestamp
#     md 13px  --text-sm     body text
#     lg 14px  --text-base   sub-headings: card, panel and section titles
#     xl 17px  --text-xl     page and head titles, the desk's .head-title
#     2xl 20px --text-3xl    the hero title and the one figure a page is opened for
SCALE_TOKENS = [
	{"token_name": "portal-text-xs", "type": "Dimension", "value": "11px"},
	{"token_name": "portal-text-sm", "type": "Dimension", "value": "12px"},
	{"token_name": "portal-text-md", "type": "Dimension", "value": "13px"},
	{"token_name": "portal-text-lg", "type": "Dimension", "value": "14px"},
	{"token_name": "portal-text-xl", "type": "Dimension", "value": "17px"},
	{"token_name": "portal-text-2xl", "type": "Dimension", "value": "20px"},
	# How tall one row of a table stands.
	{"token_name": "portal-row-pad", "type": "Dimension", "value": "10px"},
	# The room inside a card, which a row is also padded by down its sides so that the
	# two line up.
	{"token_name": "portal-card-pad", "type": "Dimension", "value": "12px"},
	# The distance between two cards, and the margin of the page around all of them.
	{"token_name": "portal-gap", "type": "Dimension", "value": "16px"},
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
html { background: var(--portal-surface-page, #ffffff); }

/* Every block carries its display inline, which outranks the browser's own
	[hidden] { display: none } rule. Without this, hiding a panel does nothing. */
[hidden] { display: none !important; }

/* State and interaction, which a block's inline styles cannot express. A block can
	carry its own :hover through a "hover:property" style key, but the chosen tile and
	the filled code box are states the script sets on an attribute, so the appearance
	of a choice lives here rather than in the script. */
input:focus-visible, select:focus-visible, button:focus-visible, a:focus-visible {
	outline: 2px solid var(--brand-primary, #0f0f0f); outline-offset: 2px;
}
input:focus, select:focus { border-color: var(--brand-primary, #0f0f0f); }
[data-code] input:not(:placeholder-shown) { border-color: var(--brand-primary, #0f0f0f); }

/* The tiles are this page's radio buttons, at the size the question deserves. The
	dot is the smallest part of the control, so choosing one restyles the whole tile. */
[data-tile][data-chosen="1"] {
	border-color: var(--brand-primary, #0f0f0f);
	box-shadow: inset 0 0 0 1px var(--brand-primary, #0f0f0f);
}
[data-tile][data-chosen="1"] [data-tile-icon] {
	background: var(--brand-primary, #0f0f0f); color: var(--brand-primary-ink, #ffffff);
}
[data-tile][data-chosen="1"] [data-tile-radio] {
	background: var(--brand-primary, #0f0f0f); border-color: var(--brand-primary, #0f0f0f);
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

# Espresso palette, from frappe/public/css/espresso/. These are the values the portal
# ships with, and the fallback that every reference below carries.
#
# Two groups, and which group a colour is in decides who owns it.
#
# The neutrals are the lender's. A grey is not neutral: PNB's greys lean red and
# Canara's lean blue, and a portal built on pure grey reads as software rather than as
# a bank. palette_overrides() below puts a trace of the lender's own colour into each
# of them.
#
# The states are ours, and a lender may not touch them. Overdue has to mean the same
# thing at every bank, and a lender whose brand is red still wants their borrower told
# in green that nothing is owed. This is the Tier 0 and Tier 1 split of
# PORTAL_DESIGN_PLAN.md section 4, written down where it can be read.
SHIPPED = {
	"surface-page": "#ffffff",
	"surface-card": "#ffffff",
	"surface-sunken": "#f8f8f8",
	"surface-hover": "#f3f3f3",
	# The same #ededed the desk reaches for as --surface-gray-3. A hover made of
	# surface-hover is five units off surface-sunken, which on the rail and in the
	# sidebar is a hover nobody can see; this is the step that reads against it.
	"surface-hover-strong": "#ededed",
	"border": "#ededed",
	"border-strong": "#999999",
	"ink": "#171717",
	"ink-muted": "#525252",
	"ink-subtle": "#7c7c7c",
	"ink-faint": "#999999",
	"ok-soft": "#e4faeb",
	"ok-deep": "#14804d",
	"warn-soft": "#fdf8ed",
	"warn-deep": "#bb6f0c",
	"danger": "#ce2c2c",
}

# The ten a lender's colour reaches, and the five it does not.
NEUTRALS = (
	"surface-page",
	"surface-card",
	"surface-sunken",
	"surface-hover",
	"surface-hover-strong",
	"border",
	"border-strong",
	"ink",
	"ink-muted",
	"ink-subtle",
	"ink-faint",
)
STATES = ("ok-soft", "ok-deep", "warn-soft", "warn-deep", "danger")


def paint(name: str) -> str:
	"""One reference to a palette token, carrying the shipped value as its fallback."""
	return f"var(--portal-{name},{SHIPPED[name]})"


# The page under everything, and a card on it. Two names for one colour today, because
# they are two decisions: every bank in the six I looked at puts colour in the band and
# leaves the page under it white, but a bank that wants an off-white page should not
# have to repaint its cards to get one.
SURFACE_PAGE = paint("surface-page")
SURFACE_CARD = paint("surface-card")
# The sidebar, a table head, the ground a card sits against.
SURFACE_SUNKEN = paint("surface-sunken")
# A row under the pointer, on a card. And the same, for a control standing on the
# sunken band, where the first one is too close to the ground it sits on to show.
SURFACE_HOVER = paint("surface-hover")
SURFACE_HOVER_STRONG = paint("surface-hover-strong")
# A hairline, and the heavier edge a control takes when the pointer is over it.
BORDER_COLOR = paint("border")
BORDER_STRONG = paint("border-strong")
# Three weights of text, and a fourth for the label nobody has to read.
INK = paint("ink")
INK_MUTED = paint("ink-muted")
INK_SUBTLE = paint("ink-subtle")
INK_FAINT = paint("ink-faint")
# On time, paid, approved. Due soon, action needed. And the mark on a required field.
OK_SOFT = paint("ok-soft")
OK_DEEP = paint("ok-deep")
WARN_SOFT = paint("warn-soft")
WARN_DEEP = paint("warn-deep")
DANGER = paint("danger")

PALETTE_TOKENS = [
	# No dark_value: dark mode is pinned light, and Builder writes a plain value rather
	# than a light-dark() pair when the second half is missing.
	{"token_name": f"portal-{name}", "type": "Color", "value": SHIPPED[name]}
	for name in NEUTRALS + STATES
]

# Every token the app writes. upsert_tokens walks this one.
PORTAL_TOKENS = BRAND_TOKENS + SCALE_TOKENS + PALETTE_TOKENS

BORDER = f"1px solid {BORDER_COLOR}"
ACTIVE_SHADOW = "0 0 1px 0 rgba(0, 0, 0, 0.14), 0 1px 3px 0 rgba(0, 0, 0, 0.14)"

# Fragments spread into the style dicts below.
COLUMN = {"display": "flex", "flexDirection": "column"}
ROW_FLEX = {"display": "flex", "alignItems": "center"}
# What a row gives up to become a link. The colour, because a row of blue text reads as
# a row of separate links rather than one destination, and the underline, because the
# whole row is the target and there is no phrase in it to underline.
LINK_ROW_STYLES = {"color": "inherit", "textDecoration": "none"}
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
ICON_CLOSE = ICON.format('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>')
# Lucide's check-check, which is the glyph the desk's own mark-all-as-read carries.
ICON_CHECK_CHECK = ICON.format('<path d="M18 6 7 17l-5-5"/><path d="m22 10-7.5 7.5L13 16"/>')
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
	"background": SURFACE_PAGE,
	"color": INK,
	"fontFamily": FONT_STACK,
	"fontVariationSettings": '"opsz" 24',
	"fontSize": "var(--portal-text-md,13px)",
	"fontWeight": "400",
	"lineHeight": "1.5",
	"WebkitFontSmoothing": "antialiased",
}

SHELL_STYLES = {"display": "flex", "minHeight": "100vh", "alignItems": "stretch"}

RAIL_STYLES = {
	**COLUMN,
	"width": "50px",
	"flexShrink": "0",
	"background": SURFACE_SUNKEN,
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
	"color": "var(--brand-mark-ink,#ffffff)",
	"display": "grid",
	"placeItems": "center",
	"marginBottom": "8px",
}
# A lender's own logo, wherever the brand name would otherwise be. Height is fixed and
# width is not, because a wordmark is wide and a roundel is not, and contain keeps both
# whole. The ceiling stops a wide one pushing the rest of the bar off the row.
LOGO_STYLES = {
	"height": "24px",
	"width": "auto",
	"maxWidth": "160px",
	"objectFit": "contain",
	"display": "block",
}
SIDE_LOGO_STYLES = {**LOGO_STYLES, "height": "22px", "maxWidth": "150px"}

RAIL_DIVIDER_STYLES = {
	"width": "20px",
	"height": "1px",
	"flexShrink": "0",
	"background": BORDER_COLOR,
	"margin": "4px 0",
}
# The desk's workspace dock item, in the portal's own colours: a 28px square that is
# nothing until the pointer is on it, and fades rather than snaps into being.
#
# The background is the whole of the hover. The glyph holds its colour throughout, as
# the dock's own does -- an icon that darkens as well reads as two things happening at
# once, and the square appearing behind it has already said everything.
RAIL_ICON_STYLES = {
	"width": "28px",
	"height": "28px",
	"borderRadius": "8px",
	"flexShrink": "0",
	"display": "grid",
	"placeItems": "center",
	"background": "transparent",
	"color": INK_MUTED,
	"textDecoration": "none",
	"cursor": "pointer",
	"transition": "background-color 0.15s ease",
	"hover:background": SURFACE_HOVER_STRONG,
}
SPACER_STYLES = {"flex": "1 1 auto"}
AVATAR_STYLES = {
	"width": "28px",
	"height": "28px",
	"borderRadius": "999px",
	"flexShrink": "0",
	"background": f"var(--brand-mark-soft,{OK_SOFT})",
	"color": f"var(--brand-mark-deep,{OK_DEEP})",
	"display": "grid",
	"placeItems": "center",
	"fontSize": "var(--portal-text-xs,11px)",
	"fontWeight": "600",
}

SIDEBAR_STYLES = {
	**COLUMN,
	"width": "220px",
	"flexShrink": "0",
	"background": SURFACE_SUNKEN,
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
	"background": SURFACE_CARD,
	"boxShadow": ACTIVE_SHADOW,
	"color": INK_MUTED,
	"cursor": "pointer",
	"zIndex": "30",
	"hover:color": INK,
	"hover:borderColor": BORDER_STRONG,
}
# One treatment for every line in the sidebar, so the whole rail reads as a single
# list rather than as six kinds of text. The rows that need to stand out -- the one
# you are on, the one under the pointer -- do it with a card and a colour, not with a
# size or a weight of their own. The two names are <b> elements, so the weight has to
# be said out loud to beat the browser's bold.
SIDE_TEXT_STYLES = {"fontSize": "var(--portal-text-md,13px)", "fontWeight": "420", "color": INK_MUTED}

# The one line that is not a row in the list: it says whose portal this is.
SIDE_HEAD_STYLES = {
	**SIDE_TEXT_STYLES,
	"fontSize": "var(--portal-text-lg,14px)",
	"fontWeight": "500",
	"color": INK,
}
SIDE_BRAND_STYLES = {**ROW_FLEX, "gap": "8px", "minHeight": "24px", "padding": "6px 8px 0"}

# overflow-y on its own makes the menu a scroll container on both axes -- the other
# axis cannot stay visible next to it -- and a scroll container cuts at its padding
# box. With no padding that box is the row itself, so the shadow the current row
# carries was being sliced flat down both sides. The negative margin gives the box
# the sidebar's own side padding to cut at instead, and the padding puts the rows
# back where they were, on the same line as the brand above and the name below.
NAV_STYLES = {
	**COLUMN,
	"flex": "1 1 auto",
	"overflowY": "auto",
	"gap": "2px",
	"padding": "0 8px",
	"margin": "0 -8px",
}
NAV_ITEM_STYLES = {
	**ROW_FLEX,
	"gap": "10px",
	"padding": "6px 8px",
	"borderRadius": "8px",
	"marginBottom": "1px",
	**SIDE_TEXT_STYLES,
	"textDecoration": "none",
	"hover:background": SURFACE_HOVER,
	"hover:color": INK,
}

# --- the two things the rail opens -------------------------------------------------
#
# The search dialog and the notifications panel belong to the frame rather than to any
# page: they are written once into the shell component and the shared client script
# brings them out. Both are built hidden, so where no script runs the magnifier is
# still a plain link to /borrower/search, and the bell, which has no page behind it,
# does nothing at all.

OVERLAY_STYLES = {
	"position": "fixed",
	"top": "0",
	"left": "0",
	"width": "100vw",
	"height": "100vh",
	"zIndex": "60",
	"display": "flex",
	"justifyContent": "center",
	"alignItems": "flex-start",
	# 28px, which is the 1.75rem a bootstrap modal sits at, because that is where the
	# desk's command box sits and this is meant to read as the same control.
	"paddingTop": "28px",
	# The dim arrives rather than appears. The desk drops a .modal-backdrop that fades
	# over 150ms while the box itself does not -- awesome_bar.js takes .fade off the
	# modal and leaves it on the backdrop -- so what transitions here is the colour and
	# not the opacity of the overlay, which would take the dialog down with it. The
	# shade the dim lands on is in SHELL_STATE_CSS, because the script owns the state.
	"background": "transparent",
	"transition": "background-color 0.15s linear",
}
DIALOG_STYLES = {
	**COLUMN,
	# 575px is the desk's $modal-md, which is what its own command box is wide. The
	# whole control is meant to read as that one, so it takes that width rather than a
	# width of its own.
	"width": "min(575px, 92vw)",
	"maxHeight": "70vh",
	"background": SURFACE_CARD,
	"borderRadius": "calc(var(--brand-radius,8px) * 1.5)",
	"boxShadow": "0 12px 40px rgba(0, 0, 0, 0.22)",
	"overflow": "hidden",
}
# 11px over and under a 13px line at the body's 1.5 leading is a 41px bar, which is the
# height the desk's own command box comes to -- 8px of padding around a 28px control.
# The padding carries the height now that the body sets at the desk's 13px rather than
# at 15px; the bar is measured against the desk, not against the text inside it.
DIALOG_HEAD_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"padding": "11px var(--portal-gap,16px)",
	"color": INK_MUTED,
	"borderBottom": BORDER,
}
# No border and no box: the dialog is the field, and a second outline inside it would
# say there is something else on this screen to fill in. The type is the body size and
# not a size up, because the desk's box sets what you type at the size of a form field.
DIALOG_INPUT_STYLES = {
	"flex": "1 1 auto",
	"minWidth": "0",
	"fontFamily": "inherit",
	"fontSize": "var(--portal-text-md,13px)",
	"color": INK,
	"border": "none",
	"outline": "none",
	"background": "transparent",
	"padding": "0",
}
# 12px around the list and 5px between the results, which is the rhythm the desk's
# command box keeps. Not the portal gap token: the token is the page's spacing and this
# list is meant to sit at the desk's.
DIALOG_BODY_STYLES = {**COLUMN, "gap": "5px", "padding": "12px", "overflowY": "auto"}
# A space between the name and what it is, not a gap: the pair reads as one phrase --
# "Personal Loan Loan account" -- the way the desk reads "Loan Lead List".
#
# 7px over and under a 13px line at the body's 1.5 leading is a 34px result, which is
# the height the desk's own results come to. The 8px at the sides puts the name 20px
# in from the edge of the dialog, where the desk puts it.
DIALOG_ROW_STYLES = {
	**ROW_FLEX,
	"gap": "5px",
	"padding": "7px 8px",
	"borderRadius": "var(--brand-radius,8px)",
	"color": INK,
	"textDecoration": "none",
	"cursor": "pointer",
}
DIALOG_ROW_TITLE_STYLES = {"fontSize": "var(--portal-text-md,13px)", "fontWeight": "600"}
DIALOG_ROW_KIND_STYLES = {"fontSize": "var(--portal-text-md,13px)", "color": INK_MUTED}
DIALOG_NOTE_STYLES = {
	"padding": "6px 20px 18px",
	"fontSize": "var(--portal-text-md,13px)",
	"color": INK_MUTED,
}
DIALOG_FOOT_STYLES = {
	**ROW_FLEX,
	"gap": "15px",
	"flexWrap": "wrap",
	"padding": "12px var(--portal-gap,16px)",
	"borderTop": BORDER,
	"background": SURFACE_SUNKEN,
	"fontSize": "var(--portal-text-sm,12px)",
	"color": INK_MUTED,
}
HINT_STYLES = {**ROW_FLEX, "gap": "5px"}
# Filled rather than outlined, which is what the desk's own .help-item is: a key cap
# reads as a solid thing to press, and an outline reads as another empty field.
KEY_STYLES = {
	"padding": "2px 5px",
	"borderRadius": "4px",
	"background": BORDER_COLOR,
	"fontSize": "var(--portal-text-xs,11px)",
	"fontWeight": "500",
	"color": INK_MUTED,
}

# The bell's panel is the desk's notifications dropdown, redrawn in portal tokens. Every
# number below is lifted from frappe/public/scss/desk/notification.scss so that a
# borrower who has also seen the desk sees the same panel: 360px wide, the header's
# hairline inset 10px rather than full-bleed, and rows that are 10px-inset cards.
#
# The colours are a rename, not a change. The desk's --text-color, --text-light,
# --text-muted, --border-color and --fg-hover-color land on the same five values as
# INK, INK_SUBTLE, INK_MUTED, BORDER_COLOR and SURFACE_HOVER -- see SHIPPED, which is
# where those values are written down -- so the panel names the portal's palette and
# still matches the desk shade for shade.
#
# The type no longer leaves the portal's scale, because the scale is now the desk's own:
# the desk sets rows in --text-base/--font-weight-regular and timestamps in --text-xs --
# 14px/420 and 12px -- which are portal-text-lg and portal-text-sm. They are still
# written out rather than named, because a row of a panel is body text and would read as
# a sub-heading under the name the portal gives 14px. See SCALE_TOKENS.
ALERTS_TEXT = "14px"
ALERTS_TEXT_SMALL = "12px"
# InterVariable's regular is 420 on the desk, not 400, and the letter-spacing comes off
# the desk's get_letterspacing table: 0.02em at regular, tightening to 0.015em at medium.
ALERTS_WEIGHT = "420"
ALERTS_TRACKING = "0.02em"
ALERTS_TRACKING_HEAVY = "0.015em"

# Fixed rather than a column of the shell: opening the bell should not reflow the page
# behind it. Which side it is fixed to depends on whether the sidebar is out, and that
# is a state the script sets, so the `left` for both cases is in SHELL_STATE_CSS.
ALERTS_STYLES = {
	**COLUMN,
	"position": "fixed",
	"top": "0",
	"height": "100vh",
	"width": "min(360px, 100vw)",
	"zIndex": "40",
	"background": SURFACE_CARD,
	"overflow": "hidden",
	"boxShadow": "rgba(0, 0, 0, 0.1) 8px 0px 8px",
}
# Margin rather than padding, because the desk's header rule is `margin: 0px 10px`: the
# hairline under it stops 10px short of each edge and lines up with the rows below it.
ALERTS_HEAD_STYLES = {
	**ROW_FLEX,
	"margin": "0 10px",
	"borderBottom": BORDER,
	"flexShrink": "0",
}
# The tab's own hairline sits on top of the header's, hence the negative bottom margin.
ALERTS_TAB_STYLES = {
	"padding": "15px 0",
	"marginRight": "20px",
	"marginBottom": "-1px",
	"border": "none",
	"borderBottom": "1px solid transparent",
	"background": "transparent",
	"fontFamily": "inherit",
	"fontSize": ALERTS_TEXT,
	"fontWeight": "500",
	"letterSpacing": ALERTS_TRACKING_HEAVY,
	"color": INK_SUBTLE,
	"cursor": "pointer",
	"hover:color": INK,
}
ALERTS_ACTION_STYLES = {
	"width": "26px",
	"height": "26px",
	"marginLeft": "4px",
	"borderRadius": "6px",
	"flexShrink": "0",
	"display": "grid",
	"placeItems": "center",
	"border": "none",
	"padding": "0",
	"background": "transparent",
	"color": INK_MUTED,
	"cursor": "pointer",
	"textDecoration": "none",
	"hover:background": SURFACE_HOVER,
	"hover:color": INK,
}
# No padding: the rows carry their own 10px margin, the way the desk's do.
ALERTS_BODY_STYLES = {**COLUMN, "flex": "1 1 auto", "overflowY": "auto"}
# A card rather than a full-bleed row, which is what makes the hover a rounded block
# floating inside the panel instead of a band across it. Nothing on the left, because
# the unread dot stands there and the desk's row is padded the same way.
ALERTS_ROW_STYLES = {
	"display": "flex",
	"alignItems": "flex-start",
	"gap": "10px",
	"margin": "10px",
	"padding": "10px 10px 10px 0",
	"borderRadius": "var(--brand-radius,8px)",
	"fontSize": ALERTS_TEXT,
	"fontWeight": ALERTS_WEIGHT,
	"letterSpacing": ALERTS_TRACKING,
	"lineHeight": "20px",
	"color": INK_SUBTLE,
	"textDecoration": "none",
	"hover:background": SURFACE_HOVER,
	"hover:color": INK_MUTED,
}
# The desk's .notification-body::before: a 6px disc on the left of every row, standing
# level with the first line of it, painted only while the row is unread.
#
# It is an element here rather than a ::before because the script has to turn it on and
# off per row, and a block can only carry one state. The script hides it rather than
# repainting it, so the colour stays here with the other colours. Whether the dot is
# drawn is the one thing about this panel that the stylesheet in the page head would
# normally own -- but that head is stored per page, and reaching it means rebuilding
# all twelve and discarding whatever has been laid out on their canvases since.
#
# The desk paints its own dot var(--invert-neutral), which no stylesheet in frappe
# defines: the desk's unread dot is invisible. INK is what that name was reaching for.
ALERTS_DOT_STYLES = {
	"width": "6px",
	"height": "6px",
	"minWidth": "6px",
	"marginTop": "16px",
	"marginLeft": "2px",
	"borderRadius": "10px",
	"flexShrink": "0",
	"background": INK,
}
# The desk's avatar-medium, which notification.scss grows to 36px for this panel alone.
ALERTS_AVATAR_STYLES = {
	"width": "36px",
	"height": "36px",
	"borderRadius": "50%",
	"flexShrink": "0",
	"marginRight": "10px",
	"background": f"var(--brand-mark-soft,{OK_SOFT})",
	"color": f"var(--brand-mark-deep,{OK_DEEP})",
	"display": "grid",
	"placeItems": "center",
	"fontSize": ALERTS_TEXT,
	"fontWeight": ALERTS_WEIGHT,
}
# The desk's .message: the lines stack with nothing between them, and the 20px line
# height off the row is what spaces them.
ALERTS_ROW_BODY_STYLES = {**COLUMN, "minWidth": "0"}
# What the desk's <b class="subject-title"> gets inside a notification: the same colour
# as the line it sits in, one weight up.
ALERTS_ROW_TITLE_STYLES = {"fontWeight": "500", "letterSpacing": ALERTS_TRACKING_HEAVY}
# Plain message text: everything it needs is on the row, and saying so beats an empty
# dict that reads like a style someone forgot to write.
ALERTS_ROW_NOTE_STYLES = {"fontWeight": ALERTS_WEIGHT, "color": "inherit"}
ALERTS_ROW_WHEN_STYLES = {"fontSize": ALERTS_TEXT_SMALL, "color": INK_MUTED}
# The desk's .notification-null-state: not a line of text at the top of the panel but a
# block held in the middle of it.
ALERTS_NOTE_STYLES = {
	"minHeight": "300px",
	"display": "flex",
	"alignItems": "center",
	"placeContent": "center",
	"padding": "0 var(--portal-card-pad,12px)",
	"textAlign": "center",
	"fontSize": ALERTS_TEXT,
	"letterSpacing": ALERTS_TRACKING,
	"color": INK_MUTED,
}

# The desk's badge, to the pixel: .es-badge at its md size and subtle variant, which is
# what a status looks like everywhere else in Frappe and so what a borrower who also
# sees the desk already reads. The numbers are the desk's own -- a 20px pill, 12px type
# on one line, 6px either side -- rather than the portal's scale, because a badge that
# grows with the page's type stops being the shape the desk made recognisable.
#
# The 1px transparent border is the desk's too: it holds the width a bordered variant
# would take, so one badge beside another never sits half a pixel off it.
#
# Tone is not here. The badge is one block repeated over the rows of a table, so a row
# cannot carry styles of its own: it names its tone in an attribute and BADGE_TONE_CSS
# paints it. What is here is the neutral it falls back to, which is what a status that
# is neither good news nor a nudge should look like.
BADGE_STYLES = {
	"display": "inline-flex",
	"alignItems": "center",
	"justifyContent": "center",
	"gap": "4px",
	"width": "fit-content",
	"flexShrink": "0",
	"height": "20px",
	"padding": "0 6px",
	"border": "1px solid transparent",
	"borderRadius": "999px",
	"fontSize": "12px",
	"fontWeight": "420",
	"lineHeight": "1",
	"letterSpacing": "0.28px",
	"whiteSpace": "nowrap",
	"overflow": "clip",
	"userSelect": "none",
	"background": SURFACE_SUNKEN,
	"color": INK_MUTED,
}

# The two tones the palette has a pair for. The desk offers six; the portal's states are
# ok, warn and danger, and danger has no soft shade to lay text on, so a rejection or a
# write-off takes the warn pair rather than a red the palette cannot make readable.
BADGE_TONE_CSS = f"""
/* A badge saying something went right, and one asking for something. Both override the
	neutral pair on the block, which is why they are here and not on it. */
[data-tone="ok"] {{ background: {OK_SOFT}; color: {OK_DEEP}; }}
[data-tone="warn"] {{ background: {WARN_SOFT}; color: {WARN_DEEP}; }}
"""

# The overview's button when nothing is waiting. It is the same anchor either way --
# one block cannot carry two sets of styles -- so the quiet variant is a rule keyed on
# what core.next_action put in the payload.
#
# A filled black button is a page saying "do this". On a day when there is nothing to
# do, the most likely next thing is still the payment page, so the button stays and
# stops shouting: the offer survives, the instruction does not.
ACTION_TONE_CSS = f"""
<style>
[data-action][data-urgent="0"] {{
	background: transparent;
	color: {INK};
	border-color: {BORDER_COLOR};
}}
[data-action][data-urgent="0"]:hover {{ background: {SURFACE_SUNKEN}; filter: none; }}
</style>
"""

# Every rule the blocks cannot carry themselves: a state the script sets, or a position
# that depends on another element. Appended to the head after HEAD_HTML, which is where
# the rest of the portal's stylesheet lives.
#
# The nav rule has to outrank two things Builder writes for that same row -- the class
# holding its base styles, and that class's :hover rule -- which a tag and two
# attributes do. The others name an attribute the script owns, so nothing competes.
SHELL_STATE_CSS = f"""
<style>
/* The sidebar row for the page being served. The rows are one block repeated over the
	menu, so the current one cannot carry different styles: it says which page it is on
	with aria-current, and this is what that looks like. */
[data-portal-nav] a[aria-current="page"] {{
	background: {SURFACE_CARD};
	box-shadow: {ACTIVE_SHADOW};
}}

/* The notifications panel stands beside the sidebar, and follows it when it is shut.
	Under the mobile breakpoint neither rail nor sidebar is there to stand beside. */
[data-alerts-panel] {{ left: 270px; }}
[data-sidebar][data-collapsed="1"] ~ [data-alerts-panel] {{ left: 50px; }}
@media (max-width: 576px) {{
	[data-alerts-panel] {{ left: 0; width: 100vw; }}
}}

/* The bell while its panel is out. The same square its own hover draws, held rather
	than passing, which is what tells you the panel came from here. The glyph does not
	change either way. */
[data-alerts-open][aria-expanded="true"] {{ background: {SURFACE_HOVER_STRONG}; }}

/* The tab in front of the other one. */
[data-alerts-tab][aria-selected="true"] {{
	color: {INK};
	border-bottom-color: var(--brand-primary,#171717);
}}

/* The result the arrow keys are on. It is also what the pointer hovers, so the two
	cannot both be styles on the block: one of them has to win, and it is this one. */
[data-search-row][data-active="1"] {{ background: {SURFACE_HOVER}; }}

/* The dim behind the search dialog, once the script has had a frame to turn it on --
	a transition does not run on the frame an element stops being display:none. The
	colour is the desk's own: $modal-backdrop-bg is --gray-800, which Espresso sets to
	the 56 named here, and .modal-backdrop.show carries it at the 0.8. Named as an
	rgba rather than a token because it is a scrim over the page and not a colour of
	the portal, which is how the shadows above it are written too. */
[data-search-overlay][data-shown="1"] {{ background: rgba(56, 56, 56, 0.8); }}

/* Whoever asked for less movement gets the dim without the fade, not without the dim. */
@media (prefers-reduced-motion: reduce) {{
	[data-search-overlay] {{ transition: none; }}
}}

/* The rules between the footer's links. The links are one block repeated over the
	lender's list, so no one of them can carry a divider of its own: the rule belongs
	to whichever link happens to follow another, which only a selector knows. The ends
	lose their padding so the row sits flush with the page head above it. */
[data-footer-links] > a + a {{ border-left: 1px solid {BORDER_COLOR}; }}
[data-footer-links] > a:first-child {{ padding-left: 0; }}
[data-footer-links] > a:last-child {{ padding-right: 0; }}
{BADGE_TONE_CSS}
</style>
"""

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
	"padding": "0 var(--portal-gap,16px)",
	"borderBottom": BORDER,
}
CRUMB_STYLES = {
	"fontSize": "var(--portal-text-lg,14px)",
	"fontWeight": "500",
	"color": INK,
}
HEAD_NOTE_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED}
HEAD_END_STYLES = {**ROW_FLEX, "marginLeft": "auto", "gap": "10px"}
BTN_STYLES = {
	"fontFamily": "inherit",
	"fontSize": "var(--portal-text-md,13px)",
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
CONTENT_STYLES = {
	**COLUMN,
	"flex": "1 1 auto",
	"padding": "var(--portal-gap,16px) var(--portal-gap,16px) calc(var(--portal-gap,16px) * 1.4)",
	"gap": "var(--portal-gap,16px)",
}
CARDS_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(auto-fit, minmax(240px, 1fr))",
	"gap": "var(--portal-gap,16px)",
}
# The overview's top strip, where the three cards are not peers. The first one carries
# the application the borrower is waiting on -- a product name and a stage, which are
# words -- and the two beside it carry figures. Given equal columns the words wrapped
# to three lines while the figures sat in half their card, so the strip is a fixed
# three, widest first, rather than the auto-fit CARDS_STYLES uses where every card
# holds a number. It folds to one column on a tablet, like every other grid here.
TOP_CARDS_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "minmax(0, 1.8fr) minmax(0, 1fr) minmax(0, 1fr)",
	"gap": "var(--portal-gap,16px)",
	"alignItems": "stretch",
}
TOP_CARDS_TABLET_STYLES = {"gridTemplateColumns": "minmax(0, 1fr)"}
NCARD_STYLES = {
	**COLUMN,
	"minHeight": "110px",
	"padding": "var(--portal-card-pad,12px)",
	"background": SURFACE_CARD,
	"border": BORDER,
	"borderRadius": "12px",
}
NCARD_HEAD_STYLES = {
	"display": "flex",
	"justifyContent": "space-between",
	"alignItems": "flex-start",
	"gap": "8px",
}
NCARD_TITLE_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "fontWeight": "500"}
NCARD_BODY_STYLES = {**COLUMN, "paddingTop": "var(--portal-card-pad,12px)"}
NUMBER_STYLES = {
	**TABULAR,
	"fontSize": "var(--portal-text-xl,17px)",
	"fontWeight": "600",
	"lineHeight": "115%",
}
NCARD_STAT_STYLES = {**TABULAR, "marginTop": "10px", "fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED}

# The two figures a borrower opened the portal to read: how much is owed, and when the
# next payment is due. See PORTAL_DESIGN_PLAN.md, stage 5.
#
# They are not in cards, and that is the whole change. A card is a container for a list,
# so a figure put in one reads as an item among several -- which is what three equal
# number cards said, with the sanctioned amount given the same weight as the two figures
# that are the reason for the visit. Standing on the page at the top of the scale, the
# two figures are the page's answer before anything under them is read.
MONEY_STYLES = {
	**COLUMN,
	"gap": "var(--portal-gap,16px)",
	"paddingBottom": "var(--portal-gap,16px)",
	"borderBottom": BORDER,
}
# Side by side where there is room and stacked where there is not, with the next
# repayment first either way: on a phone it is what has to stand above the fold.
MONEY_FIGURES_STYLES = {
	"display": "flex",
	"flexWrap": "wrap",
	"gap": "var(--portal-gap,16px) calc(var(--portal-gap,16px) * 3)",
}
MONEY_ITEM_STYLES = {**COLUMN, "gap": "2px", "minWidth": "0"}
# A row, because the label carries the "due in five days" pill beside it.
MONEY_LABEL_STYLES = {
	**ROW_FLEX,
	"gap": "8px",
	"fontSize": "var(--portal-text-sm,12px)",
	"color": INK_MUTED,
}
MONEY_FIGURE_STYLES = {
	**TABULAR,
	"fontSize": "var(--portal-text-2xl,20px)",
	"fontWeight": "600",
	"lineHeight": "115%",
	"color": INK,
}
# The date the figure is due, which is half of what the borrower came for, so it is set
# at body size rather than at the size of a footnote.
MONEY_NOTE_STYLES = {**TABULAR, "fontSize": "var(--portal-text-md,13px)", "color": INK_MUTED}
# What the third card held. A borrower checks the sanctioned amount once a year, so it
# is a line under the outstanding figure rather than a figure of its own.
MONEY_SUB_STYLES = {
	**TABULAR,
	"marginTop": "4px",
	"fontSize": "var(--portal-text-sm,12px)",
	"color": INK_SUBTLE,
}
# The button the page exists for. The one in the page head is 6px of padding wide and
# sits among the furniture; this one stands under the amount it pays.
MONEY_ACTION_STYLES = {
	**BTN_STYLES,
	"alignSelf": "flex-start",
	"fontWeight": "600",
	"padding": "10px 20px",
}

# What is waiting on the borrower, between the figures and the four cards below.
#
# Not a card itself. The cards below are things to read and this is the one thing to
# do, so putting it in the same box would file it with them. It sits on the page's own
# surface between two rules, the way the figures above it do: the top of the page is
# the part that asks something of you, and it should read as one zone.
#
# The whole strip hides when there is nothing in it. A borrower in good standing gets
# the figures and the cards, with no empty shelf in between announcing that they have
# nothing to do.
TASKS_STYLES = {
	**COLUMN,
	"gap": "8px",
	"paddingBottom": "var(--portal-gap,16px)",
	"borderBottom": BORDER,
}
TASKS_NOTE_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED}
# The repeater is the list, so the spacing between rows is set here: the rows come out
# as its children rather than the section's, and a gap on the section never reaches them.
TASKS_LIST_STYLES = {**COLUMN, "gap": "8px"}
# A row here is a bordered tile rather than a ruled line, which is the visible
# difference between a task and a record. The tables below separate rows with a rule;
# these stand apart from each other because each one is a separate piece of work.
TASK_ROW_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"padding": "10px var(--portal-card-pad,12px)",
	"border": BORDER,
	"borderRadius": "var(--brand-radius,8px)",
	"background": SURFACE_CARD,
	"hover:background": SURFACE_SUNKEN,
	**LINK_ROW_STYLES,
}
TASK_BODY_STYLES = {**COLUMN, "flex": "1 1 auto", "minWidth": "0", "gap": "2px"}

# The two-column split folds to one column on Builder's tablet breakpoint (<=1023px).
GRID_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "minmax(0, 1.9fr) minmax(0, 1fr)",
	"gap": "var(--portal-gap,16px)",
	"alignItems": "start",
}
GRID_TABLET_STYLES = {"gridTemplateColumns": "minmax(0, 1fr)"}

STACK_STYLES = {**COLUMN, "gap": "var(--portal-gap,16px)", "minWidth": "0"}
CARD_STYLES = {
	**COLUMN,
	"background": SURFACE_CARD,
	"border": BORDER,
	"borderRadius": "12px",
	"minWidth": "0",
}
CARD_HEAD_STYLES = {"padding": "var(--portal-card-pad,12px)"}
CARD_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "var(--portal-text-lg,14px)",
	"fontWeight": "600",
	"color": INK,
	"lineHeight": "1.3em",
}
CARD_SUB_STYLES = {**TABULAR, "marginTop": "5px", "fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED}
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

THEAD_STYLES = {**ROW_FLEX, "gap": "12px", "padding": "0 var(--portal-card-pad,12px) 8px", "borderBottom": BORDER}
THEAD_LABEL_STYLES = {"fontSize": "var(--portal-text-xs,11px)", "color": INK_SUBTLE}
ROW_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"padding": "var(--portal-row-pad,10px) var(--portal-card-pad,12px)",
	"borderTop": BORDER,
	"hover:background": SURFACE_SUNKEN,
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

PRIMARY_TEXT_STYLES = {"fontSize": "var(--portal-text-md,13px)", "fontWeight": "500"}
SECONDARY_TEXT_STYLES = {**TABULAR, "fontSize": "var(--portal-text-sm,12px)", "color": INK_SUBTLE}
AMOUNT_STYLES = {**TABULAR, "fontSize": "var(--portal-text-md,13px)", "fontWeight": "500"}

WHY_STYLES = {"fontSize": "var(--portal-text-xs,11px)", "color": WARN_DEEP}

LI_STYLES = {
	"display": "flex",
	"alignItems": "baseline",
	"gap": "12px",
	"padding": "var(--portal-row-pad,10px) var(--portal-card-pad,12px)",
	"borderTop": BORDER,
}
LI_DATE_STYLES = {
	**TABULAR,
	"width": "80px",
	"flexShrink": "0",
	"fontSize": "var(--portal-text-sm,12px)",
	"color": INK_MUTED,
}
LI_BODY_STYLES = {**COLUMN, "flex": "1 1 auto", "minWidth": "0", "gap": "2px"}
LI_AMT_STYLES = {**TABULAR, "flexShrink": "0", "fontSize": "var(--portal-text-md,13px)", "fontWeight": "500"}

# The activity list: the desk's own timeline, in the portal's colours. A dot per event
# on a line running down the list, and one sentence beside it.
#
# Not the dated row LI_STYLES gives the schedule, and the difference is what the two
# lists are for. A schedule is a table read down a column of dates. Activity is a record
# of things that have happened, read as sentences, and a borrower checking whether their
# payment went through wants "2 days ago" rather than a date to subtract from today.
ACTIVITY_LIST_STYLES = {**COLUMN, "gap": "0", "padding": "2px var(--portal-card-pad,12px) 10px"}
# Stretch, so the mark column is as tall as the sentence beside it however far that
# wraps. Left to itself it would be as tall as the dot, and the line would break between
# every pair of rows.
ACTIVITY_ROW_STYLES = {"display": "flex", "gap": "12px", "alignItems": "stretch"}
ACTIVITY_MARK_STYLES = {**COLUMN, "alignItems": "center", "gap": "0", "flexShrink": "0", "width": "6px"}
# The top margin is what puts the dot on the first line of the sentence rather than at
# the top of the row: the body's own padding plus half a line of it.
ACTIVITY_DOT_STYLES = {
	"width": "6px",
	"height": "6px",
	"marginTop": "15px",
	"borderRadius": "999px",
	"flexShrink": "0",
	"background": INK_SUBTLE,
}
# ACTIVITY_CSS cuts the last row's stem. A line carrying on under the final dot is a
# list that looks like it was cut off before it finished.
ACTIVITY_STEM_STYLES = {"width": "1px", "flex": "1 1 auto", "minHeight": "10px", "background": BORDER_COLOR}
ACTIVITY_BODY_STYLES = {"flex": "1 1 auto", "minWidth": "0", "padding": "8px 0", "lineHeight": "1.55"}
ACTIVITY_TITLE_STYLES = {
	"fontSize": "var(--portal-text-md,13px)",
	"fontWeight": "500",
	"color": INK,
	# Two inline spans with nothing between them render as one word. A margin says the
	# gap in a way that survives the sentence wrapping between them.
	"marginRight": "4px",
}
ACTIVITY_NOTE_STYLES = {**TABULAR, "fontSize": "var(--portal-text-md,13px)", "color": INK_MUTED}
ACTIVITY_CSS = """
<style>
[data-activity-list] > *:last-child [data-activity-stem] { display: none; }
</style>
"""

# The notice on one side and the policies on the other, which is the shape a borrower
# has read at the foot of every bank's site. Both ends wrap onto their own line under
# the mobile breakpoint rather than being cut, so nothing a regulator asks for is lost
# on a phone.
FOOTER_STYLES = {
	**ROW_FLEX,
	"justifyContent": "space-between",
	"gap": "12px 20px",
	"flexWrap": "wrap",
	"padding": "14px var(--portal-gap,16px)",
	"borderTop": BORDER,
	"fontSize": "var(--portal-text-xs,11px)",
	"color": INK_SUBTLE,
}
FOOTER_NOTE_STYLES = {"minWidth": "0"}
# No gap: the rules between the links are drawn by SHELL_STATE_CSS on each link's own
# left edge, so the space either side of one is the link's padding and stays with it
# when a row of them wraps.
FOOTER_LINKS_STYLES = {**ROW_FLEX, "flexWrap": "wrap", "minWidth": "0"}
# The last of these is the grievance contact. A lender is required to publish one, and
# a borrower reading the foot of the page is the one looking for it.
FOOTER_LINK_STYLES = {
	"color": INK_MUTED,
	"textDecoration": "none",
	"padding": "0 14px",
	"hover:color": INK,
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


def badge(key, tone_key=None, tone="", path=None):
	"""A status, in the shape the desk gives one.

	`tone_key` is a second key from the page data, bound to the attribute BADGE_TONE_CSS
	reads. A row in a repeated table needs it, because the block is shared and only the
	payload can tell one row from another. `tone` is for the badge that stands alone and
	always means the same thing, which can say so on the block and bind nothing.
	"""
	node = bound("span", key, styles=BADGE_STYLES, path=path, attributes={"data-tone": tone})
	if tone_key:
		bind(node, tone_key, property="data-tone", type="attribute")

	return node


def linked(key, styles=None, children=None, **kwargs):
	"""A row that carries its own destination, for a repeater over records."""
	node = block("a", styles=styles, children=children, attributes={"href": "#"}, **kwargs)
	return bind(node, key, property="href", type="attribute")


def repeater(key, row, path=None, styles=None, element="div", **kwargs):
	"""A block that renders its one child once per row of `key`.

	The rows come out as children of this block, not of its parent, so a grid or a
	flex row has to be styled *here*. Styled on the parent instead, every row lands in
	the parent's first cell: the repeater itself is that cell.

	`element` is for the repeater that *is* the landmark it fills -- a <nav> of links
	rather than a <div> of them -- so the tree does not gain a wrapper whose only job
	is to hold a tag name.
	"""
	node = block(element, path=path, styles=styles, isRepeaterBlock=True, children=[row], **kwargs)
	node["dataKey"] = {"key": key, "type": "key", "property": "dataKey", "comesFrom": "dataScript"}

	return node


def channels(colour: str):
	"""The three channels of a #rgb or #rrggbb colour, or None if it is neither.

	A Color field holds whatever the picker wrote, and an empty one holds nothing, so
	every colour read from settings comes through here before it is believed.
	"""
	digits = (colour or "").strip().lstrip("#")
	if len(digits) == 3:
		digits = "".join(digit * 2 for digit in digits)

	if len(digits) != 6 or any(digit not in "0123456789abcdefABCDEF" for digit in digits):
		return None

	return tuple(int(digits[index : index + 2], 16) for index in (0, 2, 4))


def to_linear(channel: int) -> float:
	ratio = channel / 255
	return ratio / 12.92 if ratio <= 0.03928 else ((ratio + 0.055) / 1.055) ** 2.4


def from_linear(part: float) -> int:
	ratio = part * 12.92 if part <= 0.0031308 else 1.055 * part ** (1 / 2.4) - 0.055
	return round(max(0.0, min(1.0, ratio)) * 255)


def luminance(rgb) -> float:
	"""Relative luminance as WCAG defines it: 0 for black, 1 for white."""
	red, green, blue = (to_linear(channel) for channel in rgb)

	return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def relight(rgb, target: float) -> str:
	"""The same colour at a given luminance, so one brand colour yields a family.

	The scaling is done on the linear components, which keeps the hue: converting back
	through the sRGB curve gives a colour that reads as the one the lender chose, only
	darker. It is used to darken and never to lighten, because brightening a saturated
	colour clips a channel and the hue moves.
	"""
	parts = [to_linear(channel) for channel in rgb]
	current = 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]
	scale = target / current if current else 0

	return "#" + "".join(f"{from_linear(part * scale):02x}" for part in parts)


def tint(rgb, weight: float = 0.12) -> str:
	"""The colour laid thinly over white, for a chip or a wash behind it."""
	return "#" + "".join(
		f"{round(channel * weight + 255 * (1 - weight)):02x}" for channel in rgb
	)


# Dark enough to read on the tint above it, and no darker, so the accent is still
# recognisable as the colour the lender picked.
DEEP_LUMINANCE = 0.12

# APCA, from the W3C's published algorithm. The names are the ones the algorithm uses,
# so the numbers can be checked against it rather than taken on trust.
APCA_BLACK_THRESHOLD = 0.022
APCA_BLACK_CLAMP = 1.414
APCA_SCALE = 1.14
APCA_LOW_CLIP = 0.1
APCA_OFFSET = 0.027


def apca_y(rgb) -> float:
	"""Screen luminance as APCA measures it, which is not what WCAG measures.

	The plain 2.4 exponent, with no sRGB curve: APCA models what a screen emits rather
	than what the sRGB standard encodes. The clamp near black is what stops two very
	dark colours reporting a contrast that nobody can see.
	"""
	red, green, blue = ((channel / 255) ** 2.4 for channel in rgb)
	brightness = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue

	if brightness >= APCA_BLACK_THRESHOLD:
		return brightness

	return brightness + (APCA_BLACK_THRESHOLD - brightness) ** APCA_BLACK_CLAMP


def apca(text, background) -> float:
	"""How readable this text colour is on this background, 0 to about 106.

	Returned without its sign, because the only question asked of it here is which of
	two inks reads better. About 60 is body text, about 45 is a large label.
	"""
	text_y, back_y = apca_y(text), apca_y(background)

	if back_y > text_y:
		raw = (back_y**0.56 - text_y**0.57) * APCA_SCALE
		return 0.0 if raw < APCA_LOW_CLIP else (raw - APCA_OFFSET) * 100

	raw = (back_y**0.65 - text_y**0.62) * APCA_SCALE

	return 0.0 if -raw < APCA_LOW_CLIP else -(raw + APCA_OFFSET) * 100


def ink_for(rgb) -> str:
	"""Whichever of white and the dark ink reads better on this colour.

	APCA rather than the WCAG ratio. WCAG puts the crossover at one luminance for every
	hue, and luminance is not how the eye reads a colour: it over-weights green and
	under-weights blue, so a mid green and a mid yellow both get the wrong ink. Those
	are the two colours nobody demos and somebody eventually picks.
	"""
	light, dark = SHIPPED["surface-card"], SHIPPED["ink"]

	return light if apca(channels(light), rgb) >= apca(channels(dark), rgb) else dark


def to_hsl(rgb):
	"""Hue in turns, saturation and lightness, all 0 to 1."""
	red, green, blue = (channel / 255 for channel in rgb)
	high, low = max(red, green, blue), min(red, green, blue)
	lightness = (high + low) / 2
	spread = high - low

	if not spread:
		return 0.0, 0.0, lightness

	saturation = spread / (1 - abs(2 * lightness - 1))
	if high == red:
		hue = ((green - blue) / spread) % 6
	elif high == green:
		hue = (blue - red) / spread + 2
	else:
		hue = (red - green) / spread + 4

	return hue / 6, saturation, lightness


def from_hsl(hue: float, saturation: float, lightness: float) -> str:
	"""The colour those three describe, as #rrggbb."""
	spread = (1 - abs(2 * lightness - 1)) * saturation
	second = spread * (1 - abs((hue * 6) % 2 - 1))
	base = lightness - spread / 2
	parts = [
		(spread, second, 0.0),
		(second, spread, 0.0),
		(0.0, spread, second),
		(0.0, second, spread),
		(second, 0.0, spread),
		(spread, 0.0, second),
	][min(int(hue * 6), 5)]

	return "#" + "".join(f"{round((part + base) * 255):02x}" for part in parts)


# How much of the lender's colour a neutral carries. Held as a chroma rather than as a
# saturation, because saturation buys almost no colour at the top and the bottom of the
# scale, which is exactly where the neutrals are: a flat saturation would tint the mid
# greys and leave the page and the ink untouched. A chroma is the same amount of colour
# at every lightness.
NEUTRAL_CHROMA = 0.03


def hue_shift(colour: str, hue: float) -> str:
	"""The same luminance, carrying NEUTRAL_CHROMA of a given hue.

	Two steps, and the second is the one that matters. Mixing the hue in at a fixed
	lightness is not enough, because lightness is not luminance: the eye reads a yellow
	grey as brighter than a blue grey of the same lightness, and left there the body
	text on a yellow-branded portal loses five percent of its contrast. So the tinted
	colour is then put back to the luminance it started at. Contrast is a ratio of
	luminances and nothing else, so every ratio on the page comes out unchanged.

	White is returned unchanged. There is no room for chroma at full lightness, and
	that is the right answer anyway: every one of the six bank sites puts its colour in
	the band across the top and leaves the page under it white.
	"""
	rgb = channels(colour)
	_, _, lightness = to_hsl(rgb)
	headroom = 1 - abs(2 * lightness - 1)
	if not headroom:
		return colour

	tinted = from_hsl(hue, min(NEUTRAL_CHROMA / headroom, 1.0), lightness)

	return relight(channels(tinted), luminance(rgb))


def brand_overrides() -> dict:
	"""The token values a lender has configured, keyed by token name.

	Anything left unset is left out, so the shipped default in BRAND_TOKENS stands.
	That is what makes the settings safe to add to a running site: a bank that has
	filled nothing in gets the portal it had yesterday.
	"""
	from lending.portal.core import portal_settings

	settings = portal_settings("portal_brand_color", "portal_accent_color")
	overrides = {}

	primary = channels(settings.portal_brand_color)
	if primary:
		overrides["brand-primary"] = settings.portal_brand_color.strip()
		overrides["brand-primary-ink"] = ink_for(primary)

	accent = channels(settings.portal_accent_color)
	if accent:
		overrides["brand-mark"] = settings.portal_accent_color.strip()
		overrides["brand-mark-ink"] = ink_for(accent)
		overrides["brand-mark-soft"] = tint(accent)
		overrides["brand-mark-deep"] = (
			relight(accent, DEEP_LUMINANCE) if luminance(accent) > DEEP_LUMINANCE else overrides["brand-mark"]
		)

	return overrides


# Below this there is no hue to take. A lender who picks a grey or a near black has
# picked a neutral already, and reading a hue off it would give whichever of the three
# channels rounding happened to leave highest.
BRAND_SATURATION_FLOOR = 0.15


def palette_overrides() -> dict:
	"""Every neutral, carrying a trace of the lender's own colour.

	This is the half of white labelling that the colour fields alone do not reach. A
	lender sets a brand colour and gets a blue button on a portal whose greys are still
	the ones Frappe ships, and grey is the largest surface on the page.

	Only the hue moves. Each neutral keeps the lightness it ships with, so a border
	stays as strong a border and the body text stays as readable as it was designed to
	be. The states are left out on purpose: see SHIPPED.
	"""
	from lending.portal.core import portal_settings

	settings = portal_settings("portal_brand_color")
	brand = channels(settings.portal_brand_color)
	if not brand:
		return {}

	hue, saturation, _ = to_hsl(brand)
	if saturation < BRAND_SATURATION_FLOOR:
		return {}

	return {f"portal-{name}": hue_shift(SHIPPED[name], hue) for name in NEUTRALS}


def upsert_tokens():
	"""Create the portal's tokens under readable, stable document names.

	Builder Token.autoname only falls back to a UUID when no name is set, and the
	emitted CSS custom property is --<document name>. Naming them after the token
	gives every site the same --brand-* and --portal-* properties, so the references
	above are portable; left to autoname, each site would emit a different UUID.

	This is also how a lender's own colours reach the page. Lending Settings.on_update
	calls it, so saving one desk form restyles every portal page at once, and the
	after_migrate hook calls it again so that migrating cannot quietly hand a lender
	back the colours the app ships with.
	"""
	overrides = brand_overrides() | palette_overrides()
	changed = False

	for token in PORTAL_TOKENS:
		name = token["token_name"]
		token = dict(token)

		if name in overrides:
			token["value"] = overrides[name]
			# Dark mode is pinned light -- see PORTAL_CUSTOMIZATION_PLAN.md B.3 -- but a
			# dark_value left behind would be the one value on the record still holding
			# the colour the lender replaced.
			if "dark_value" in token:
				token["dark_value"] = overrides[name]

		if frappe.db.exists("Builder Token", name):
			doc = frappe.get_doc("Builder Token", name)
			# An unchanged record is left alone. Saving one in developer mode exports it
			# back over lending/builder_files/, so a no-op save would rewrite the app's
			# own source every time anybody saved Lending Settings.
			if all(doc.get(field) == value for field, value in token.items()):
				continue

			doc.update(token)
			doc.save()
			changed = True
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

		changed = True

	if changed:
		clear_builder_token_cache()


def card(title, subtitle_key, body, action=None, visible_key=None):
	"""A titled panel with a subtitle from data. Every portal page is built of these.

	`action` is the one thing the card offers to press, sat at the end of its title
	row. Without one the head is the title and its subtitle, as it always was.

	`visible_key` drops the whole card when that key is empty. A card whose subtitle
	says "Nothing to show" is still a box, a heading and a rule spent on saying that
	there is nothing, and four of them side by side is a page reporting its own
	emptiness four times. A card only takes this where some other card is certain to
	remain, so the page never empties out completely.
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

	node = block("section", styles=CARD_STYLES, children=[head, body])
	if visible_key:
		node["visibilityCondition"] = visible_key

	return node


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
		styles={**ROW_STYLES, **LINK_ROW_STYLES},
		children=[
			block("div", styles=RECORD_COLUMNS[index], children=children)
			for index, children in enumerate(columns)
		],
	)

	return block("div", children=[head, repeater(key, row)])


def timeline_rows(key, title_key, sub_key, url_key=None):
	"""A dated event per row: when it happened, what it was, how much it was for.

	`url_key` makes the whole row the way into the record the event belongs to. A page
	already showing that record passes none, and the row stays a plain one: a link back
	to the page you are on is a dead end wearing a pointer.

	The second line hides on an empty value. A list of one loan's instalments has
	nothing to put there -- the card's own subtitle has already named the loan, and
	repeating it down every row is the list telling you four times what it told you
	once -- and an empty div would still take its gap and leave the rows uneven.
	"""
	sub = bound("div", sub_key, styles=SECONDARY_TEXT_STYLES)
	sub["visibilityCondition"] = sub_key

	children = [
		bound("span", "date", styles=LI_DATE_STYLES),
		block(
			"div",
			styles=LI_BODY_STYLES,
			children=[bound("div", title_key, styles=PRIMARY_TEXT_STYLES), sub],
		),
		bound("span", "amount", styles=LI_AMT_STYLES),
	]
	row = (
		linked(url_key, styles={**LI_STYLES, **LINK_ROW_STYLES, "hover:background": SURFACE_SUNKEN}, children=children)
		if url_key
		else block("div", styles=LI_STYLES, children=children)
	)

	return repeater(key, row)


def activity_list(key, title_key, note_key, url_key=None, date_key=None):
	"""One event per row: a dot on the line, then a sentence saying what happened.

	The sentence is two spans and not five, because the weight changes once and the
	rest of it is one grey clause: what happened, in ink, and then how much, which loan
	and how long ago, joined in the data layer. Builder binds one key into one element,
	so a block that wanted the parts separately would need a span each and a separator
	between them that had to know which of its neighbours were empty.

	`date_key` puts the day it happened in the sentence's tooltip. "2 days ago" is the
	faster read and the one the list is for, but the date is what a borrower needs the
	moment they go looking for the entry on a statement, and it costs no room here.
	"""
	note = bound("span", note_key, styles=ACTIVITY_NOTE_STYLES, attributes={"title": ""})
	if date_key:
		bind(note, date_key, property="title", type="attribute")

	children = [
		block(
			"div",
			styles=ACTIVITY_MARK_STYLES,
			children=[
				block("span", styles=ACTIVITY_DOT_STYLES),
				block("span", styles=ACTIVITY_STEM_STYLES, attributes={"data-activity-stem": "1"}),
			],
		),
		block(
			"div",
			styles=ACTIVITY_BODY_STYLES,
			children=[bound("span", title_key, styles=ACTIVITY_TITLE_STYLES), note],
		),
	]
	row = (
		linked(url_key, styles={**ACTIVITY_ROW_STYLES, **LINK_ROW_STYLES}, children=children)
		if url_key
		else block("div", styles=ACTIVITY_ROW_STYLES, children=children)
	)

	# The marker ACTIVITY_CSS hangs the last row's cut stem off. On the list rather than
	# on the row, because the rows are one repeated block and every copy carries the
	# same attributes -- only their position tells them apart.
	return repeater(key, row, styles=ACTIVITY_LIST_STYLES, attributes={"data-activity-list": "1"})


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


# --- the lead card: the one a borrower opens the page for --------------------------
#
# The application detail page leads with the product, the reference and how far the
# file has got, because "where has it reached" is the question that brings a borrower
# here. Everything below it answers "and what did I ask for".
#
# LEAD_ rather than HERO_: the public pages already own that prefix, and a second
# HERO_TITLE_STYLES would silently replace theirs -- this file is read top to bottom
# and the later name wins.

LEAD_STYLES = {
	**CARD_STYLES,
	"flexDirection": "row",
	"alignItems": "stretch",
	"gap": "0",
	"overflow": "hidden",
}
LEAD_TABLET_STYLES = {"flexDirection": "column"}
# A decorative panel, not a picture of anything: the portal ships no product artwork
# and a lender's own would have to be uploaded per product.
LEAD_ART_STYLES = {
	"display": "grid",
	"placeItems": "center",
	"width": "180px",
	"flexShrink": "0",
	"background": SURFACE_SUNKEN,
	"color": "var(--brand-primary,#171717)",
	"borderRight": BORDER,
}
LEAD_ART_TABLET_STYLES = {
	"width": "auto",
	"padding": "20px 0",
	"borderRight": "none",
	"borderBottom": BORDER,
}
LEAD_BODY_STYLES = {
	**COLUMN,
	"flex": "1 1 auto",
	"minWidth": "0",
	"gap": "18px",
	"padding": "20px var(--portal-gap,16px)",
}
LEAD_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "var(--portal-text-xl,17px)",
	"fontWeight": "600",
	"color": INK,
	"lineHeight": "1.3em",
}
LEAD_REF_STYLES = {**TABULAR, "marginTop": "4px", "fontSize": "var(--portal-text-sm,12px)", "color": INK_SUBTLE}
LEAD_HEADLINE_STYLES = {
	"margin": "0",
	"fontSize": "var(--portal-text-lg,14px)",
	"fontWeight": "600",
	"color": INK,
}
LEAD_NOTE_STYLES = {"marginTop": "4px", "fontSize": "var(--portal-text-md,13px)", "color": INK_MUTED}

# The tracker laid across rather than down. Everything that distinguishes one step
# from another -- the filled tick, the joining line, the underline under the step in
# progress -- is a state the data names and APPLICATION_CSS draws, because the steps
# are one block repeated and so cannot carry a style each.
TRACK_STYLES = {"display": "flex", "alignItems": "flex-start", "gap": "0"}
TRACK_STEP_STYLES = {
	**COLUMN,
	"alignItems": "center",
	"gap": "8px",
	"flex": "1 1 0",
	"minWidth": "0",
	"position": "relative",
	"textAlign": "center",
}
TRACK_MARK_STYLES = {
	"display": "grid",
	"placeItems": "center",
	"width": "26px",
	"height": "26px",
	"borderRadius": "999px",
	"flexShrink": "0",
	"position": "relative",
	"zIndex": "1",
	"background": SURFACE_CARD,
	"border": f"2px solid {BORDER_STRONG}",
	"color": INK_FAINT,
	"fontSize": "var(--portal-text-sm,12px)",
	"lineHeight": "1",
}
TRACK_LABEL_STYLES = {
	"fontSize": "var(--portal-text-sm,12px)",
	"color": INK_MUTED,
	"paddingBottom": "6px",
	"borderBottom": "2px solid transparent",
}

# --- the preview: four sections, one card, one at a time ---------------------------

TABLIST_STYLES = {
	**ROW_FLEX,
	"gap": "20px",
	"flexWrap": "wrap",
	"padding": "0 var(--portal-card-pad,12px)",
	"borderBottom": BORDER,
}
TAB_STYLES = {
	"padding": "0 0 10px",
	"marginBottom": "-1px",
	"border": "none",
	"borderBottom": "2px solid transparent",
	"background": "transparent",
	"fontFamily": "inherit",
	"fontSize": "var(--portal-text-md,13px)",
	"fontWeight": "500",
	"color": INK_SUBTLE,
	"cursor": "pointer",
	"hover:color": INK,
}
# Three across, because that is what the pairs on this page are: a short label over a
# short value. Two on a tablet, one on a phone -- Builder's own breakpoints.
PAIR_GRID_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
	"gap": "18px var(--portal-gap,16px)",
	"padding": "var(--portal-card-pad,12px)",
}
PAIR_GRID_TABLET_STYLES = {"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"}
PAIR_GRID_MOBILE_STYLES = {"gridTemplateColumns": "minmax(0, 1fr)"}
PAIR_CELL_STYLES = {**COLUMN, "gap": "4px", "minWidth": "0"}

# The row over the page: where the borrower came from, and the day they are reading.
CREST_STYLES = {**ROW_FLEX, "justifyContent": "space-between", "gap": "12px", "flexWrap": "wrap"}
BACK_STYLES = {
	**ROW_FLEX,
	"gap": "8px",
	"fontSize": "var(--portal-text-md,13px)",
	"color": INK_MUTED,
	"textDecoration": "none",
	"hover:color": INK,
}
AS_ON_STYLES = {**TABULAR, "fontSize": "var(--portal-text-sm,12px)", "color": INK_SUBTLE}


def step_track(key):
	"""The stage tracker as one row across, one step per stage.

	`code` rides in as an attribute rather than as text: it is what APPLICATION_CSS
	matches on to fill the tick, colour the line into it and underline the step being
	worked on. The tick character itself still comes from `marker`, so a page that
	renders before the stylesheet does still says which stages are behind.
	"""
	mark = bound("span", "marker", styles=TRACK_MARK_STYLES, attributes={"data-step-mark": "1"})
	step = block(
		"div",
		styles=TRACK_STEP_STYLES,
		attributes={"data-track-step": "1"},
		children=[mark, bound("div", "short", styles=TRACK_LABEL_STYLES, attributes={"data-step-label": "1"})],
	)

	return repeater(key, bind(step, "code", property="data-step-state", type="attribute"), styles=TRACK_STYLES, attributes={"data-track": "1"})


def lead_card(title_key, ref_key, steps_key, headline_key, note_key, art):
	"""The card the page opens with: what this is, how far it has got, what that means."""
	return block(
		"section",
		styles=LEAD_STYLES,
		tabletStyles=LEAD_TABLET_STYLES,
		children=[
			block(
				"div",
				styles=LEAD_ART_STYLES,
				tabletStyles=LEAD_ART_TABLET_STYLES,
				html=art,
				attributes={"data-lead-art": "1", "aria-hidden": "true"},
			),
			block(
				"div",
				styles=LEAD_BODY_STYLES,
				children=[
					block(
						"div",
						children=[
							bound("h1", title_key, styles=LEAD_TITLE_STYLES),
							bound("div", ref_key, styles=LEAD_REF_STYLES),
						],
					),
					step_track(steps_key),
					block(
						"div",
						children=[
							bound("h2", headline_key, styles=LEAD_HEADLINE_STYLES),
							bound("div", note_key, styles=LEAD_NOTE_STYLES),
						],
					),
				],
			),
		],
	)


def pair_grid(key, with_detail=False, marker=False):
	"""The pair rows again, laid out across the card instead of down it."""
	label = bound("div", "label", styles=SECONDARY_TEXT_STYLES)
	if marker:
		# The tick belongs beside what it is about, not on a line of its own: a cell
		# that opened with a bare mark would read as a column of ticks.
		label = block(
			"div",
			styles={**ROW_FLEX, "gap": "6px", "minWidth": "0"},
			children=[
				bound("span", "marker", styles={"color": OK_DEEP, "flexShrink": "0"}),
				bound("span", "label", styles=SECONDARY_TEXT_STYLES),
			],
		)

	lines = [label, bound("div", "value", styles=PRIMARY_TEXT_STYLES)]
	if with_detail:
		detail = bound("div", "detail", styles=SECONDARY_TEXT_STYLES)
		detail["visibilityCondition"] = "detail"
		lines.append(detail)

	return repeater(
		key,
		block("div", styles=PAIR_CELL_STYLES, children=lines),
		styles=PAIR_GRID_STYLES,
		tabletStyles=PAIR_GRID_TABLET_STYLES,
		mobileStyles=PAIR_GRID_MOBILE_STYLES,
	)


def preview(title, subtitle_key, sections):
	"""One card holding several sections, of which one shows at a time.

	`sections` is (name, label, note_key, body). The first is the one that opens, and
	it is marked open here rather than left to the script, so the card is not blank in
	the moment before the script runs -- or at all, if it never does.
	"""
	tabs = []
	panels = []
	for index, (name, label, note_key, body) in enumerate(sections):
		first = index == 0
		tabs.append(
			block(
				"button",
				styles=TAB_STYLES,
				html=label,
				attributes={
					"type": "button",
					"role": "tab",
					"data-tab": name,
					"aria-selected": "true" if first else "false",
				},
			)
		)
		panel = block(
			"div",
			children=[note_panel(note_key), body],
			attributes={"role": "tabpanel", "data-panel": name},
		)
		if not first:
			panel["attributes"]["hidden"] = "hidden"
		panels.append(panel)

	group = block(
		"div",
		attributes={"data-tabs": "1"},
		children=[block("div", styles=TABLIST_STYLES, attributes={"role": "tablist"}, children=tabs), *panels],
	)

	return card(title, subtitle_key, group)


# Rules the blocks on the application page cannot carry themselves, because the step
# they style is one block repeated over the stages. Passed to build_page as that
# page's own head CSS, so adding it costs one page rebuild rather than eleven.
APPLICATION_CSS = f"""
<style>
[data-lead-art] svg {{ width: 56px; height: 56px; stroke-width: 1.4; }}

/* The line joining one step to the one before it. It starts behind the tick -- the
	tick sits on its own stacking level and carries the card's background -- and runs
	back to the middle of the step before. */
[data-track-step]::before {{
	content: "";
	position: absolute;
	top: 12px;
	right: 50%;
	width: 100%;
	height: 2px;
	background: {BORDER_COLOR};
}}
[data-track-step]:first-child::before {{ display: none; }}

/* A stage that is behind you, and the line you crossed to get there. The line into
	the stage in progress is crossed too, which is why it is coloured the same. */
[data-step-state="done"]::before,
[data-step-state="current"]::before {{ background: {OK_DEEP}; }}
/* The tick is the card showing through the fill, which is why it is the card's own
	colour rather than a white of its own: a lender with an off-white card gets a tick
	that matches everything else punched out of a fill. */
[data-step-state="done"] [data-step-mark] {{
	background: {OK_DEEP};
	border-color: {OK_DEEP};
	color: {SURFACE_CARD};
}}

/* The stage being worked on: the lender's colour, and the underline that says this
	is the one the page is about. */
[data-step-state="current"] [data-step-mark] {{
	background: var(--brand-primary,#171717);
	border-color: var(--brand-primary,#171717);
	color: var(--brand-primary-ink,#ffffff);
}}
[data-step-state="current"] [data-step-label] {{
	color: {INK};
	font-weight: 600;
	border-bottom-color: var(--brand-primary,#171717);
}}

/* Across is only worth it while the steps have room. Under Builder's mobile
	breakpoint five of them would be five stacks of broken words, so the tracker
	turns back into the list it used to be and the joining line turns with it. */
@media (max-width: 576px) {{
	[data-track] {{ flex-direction: column; align-items: stretch; }}
	[data-track-step] {{
		flex-direction: row;
		align-items: center;
		gap: 12px;
		text-align: left;
		padding: 6px 0;
	}}
	[data-track-step]::before {{
		top: auto;
		bottom: 50%;
		right: auto;
		left: 12px;
		width: 2px;
		height: 100%;
	}}
	[data-step-label] {{ border-bottom: none; padding-bottom: 0; }}
}}

/* The section of the preview being read. */
[data-tab][aria-selected="true"] {{
	color: {INK};
	border-bottom-color: var(--brand-primary,#171717);
}}
</style>
"""


# --- the public pages: no sidebar, one centred column -----------------------------

PUBLIC_PAGE_STYLES = {
	**COLUMN,
	"minHeight": "100vh",
	"alignItems": "center",
	"padding": "0 20px 64px",
	"gap": "0",
	"background": SURFACE_SUNKEN,
}
PUBLIC_COLUMN_STYLES = {**COLUMN, "width": "100%", "maxWidth": "720px", "gap": "var(--portal-gap,16px)"}

FIELD_STYLES = {**COLUMN, "gap": "6px", "padding": "8px 12px"}
LABEL_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "fontWeight": "500", "color": INK_MUTED}
INPUT_STYLES = {
	"fontFamily": "inherit",
	"fontSize": "var(--portal-text-md,13px)",
	"padding": "10px 12px",
	"borderRadius": "var(--brand-radius,10px)",
	"border": BORDER,
	"background": SURFACE_CARD,
	"color": INK,
	"width": "100%",
	"boxSizing": "border-box",
	"hover:borderColor": BORDER_STRONG,
}
# The search page's one control. The box takes whatever width is going and the button
# takes none, so the pair reads as one field rather than as two things side by side.
SEARCH_ROW_STYLES = {**ROW_FLEX, "gap": "10px", "padding": "12px"}
SEARCH_BOX_STYLES = {**INPUT_STYLES, "flex": "1 1 auto"}

# An answer already given, shown back rather than asked for twice.
ECHO_INPUT_STYLES = {**INPUT_STYLES, "background": SURFACE_HOVER, "color": INK_MUTED, "hover:borderColor": BORDER_COLOR}
ECHO_NOTE_STYLES = {**ROW_FLEX, "gap": "5px", "fontSize": "var(--portal-text-xs,11px)", "fontWeight": "500", "color": OK_DEEP}
SUBMIT_ROW_STYLES = {**ROW_FLEX, "gap": "10px", "padding": "12px", "borderTop": BORDER}
RESULT_STYLES = {
	**COLUMN,
	"gap": "8px",
	"padding": "16px",
	"background": OK_SOFT,
	"borderRadius": "12px",
	"color": INK,
}
ERROR_STYLES = {
	"padding": "12px 16px",
	"background": WARN_SOFT,
	"borderRadius": "8px",
	"fontSize": "var(--portal-text-sm,12px)",
	"color": WARN_DEEP,
}


def label_block(label, required=True):
	"""One field label, carrying the asterisk people look for.

	Required-ness was only in the note above the form before, so the one field holding
	a visitor up was whichever they had skipped, and the form would not say which.
	"""
	mark = f' <span style="color: {DANGER}">*</span>' if required else ""

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
	"background": SURFACE_CARD,
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
	"fontSize": "var(--portal-text-md,13px)",
	"fontWeight": "500",
	"color": INK_MUTED,
	"textDecoration": "none",
	"hover:color": INK,
}
# The way back in, for a visitor who has applied before. A pill rather than a third
# link, because it is the only thing in the bar anybody arrives looking for.
PILL_LINK_STYLES = {
	**ROW_FLEX,
	"gap": "7px",
	"padding": "7px 14px",
	"borderRadius": "999px",
	"border": BORDER,
	"background": SURFACE_CARD,
	"fontSize": "var(--portal-text-md,13px)",
	"fontWeight": "500",
	"color": INK,
	"textDecoration": "none",
	"whiteSpace": "nowrap",
	"hover:borderColor": BORDER_STRONG,
}

HERO_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "var(--portal-text-2xl,20px)",
	"lineHeight": "1.15",
	"fontWeight": "600",
	"color": INK,
	"letterSpacing": "-0.02em",
	"maxWidth": "20ch",
}
HERO_TITLE_MOBILE_STYLES = {"fontSize": "var(--portal-text-xl,17px)"}
HERO_INTRO_STYLES = {
	"margin": "0",
	"fontSize": "var(--portal-text-md,13px)",
	"lineHeight": "1.55",
	"color": INK_MUTED,
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
	"background": OK_SOFT,
	"color": OK_DEEP,
	# Not on the scale: this is a glyph inside a fixed circle, so it may not grow.
	"fontSize": "10px",
	"fontWeight": "600",
}
TRUST_TEXT_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED}


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
	"background": (
		f"linear-gradient(150deg, {SURFACE_CARD} 0%, {SURFACE_SUNKEN} 60%,"
		f" var(--brand-mark-soft,{OK_SOFT}) 220%)"
	),
	"boxShadow": ACTIVE_SHADOW,
}
START_CARD_MOBILE_STYLES = {"padding": "24px 20px"}
START_COPY_STYLES = {**COLUMN, "gap": "6px", "minWidth": "0"}
START_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "var(--portal-text-xl,17px)",
	"fontWeight": "600",
	"letterSpacing": "-0.01em",
	"color": INK,
}
START_NOTE_STYLES = {"margin": "0", "fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED}

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
	# Not on the scale: this is a glyph inside a fixed circle, so it may not grow.
	"fontSize": "11px",
	"fontWeight": "600",
}
BENEFIT_TITLE_STYLES = {"fontSize": "var(--portal-text-md,13px)", "fontWeight": "600", "color": INK}
BENEFIT_NOTE_STYLES = {"margin": "0", "fontSize": "var(--portal-text-sm,12px)", "color": INK_SUBTLE, "lineHeight": "1.5"}


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
PROGRESS_NAME_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "fontWeight": "600", "color": INK}
PROGRESS_COUNT_STYLES = {**TABULAR, "fontSize": "var(--portal-text-xs,11px)", "fontWeight": "500", "color": INK_SUBTLE}
PROGRESS_TRACK_STYLES = {
	"width": "100%",
	"height": "4px",
	"borderRadius": "999px",
	"background": BORDER_COLOR,
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
#
# PANEL_* here is the apply wizard's step card, and has nothing to do with the bell's
# notifications panel further up, which is ALERTS_*. They were both PANEL_* once: three
# of the names collided, Python kept whichever was defined last, and the notifications
# panel spent that time wearing this card's styles -- a column head and no width, in a
# thing meant to be a fixed 360px rail. Keep the two prefixes apart.

WIZARD_STYLES = {**COLUMN, "gap": "18px"}
PANEL_STYLES = {
	**COLUMN,
	"background": SURFACE_CARD,
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
	"fontSize": "var(--portal-text-xs,11px)",
	"fontWeight": "600",
	"letterSpacing": "0.06em",
	"textTransform": "uppercase",
	"color": INK_FAINT,
}
PANEL_TITLE_STYLES = {"margin": "0", "fontSize": "var(--portal-text-lg,14px)", "fontWeight": "600", "color": INK}
PANEL_SUB_STYLES = {"margin": "0", "fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED, "lineHeight": "1.5"}

# One question per screen, asked at the size of the only thing being asked.
QUESTION_TITLE_STYLES = {
	"margin": "0",
	"fontSize": "var(--portal-text-xl,17px)",
	"lineHeight": "1.2",
	"fontWeight": "600",
	"letterSpacing": "-0.02em",
	"color": INK,
}
QUESTION_TITLE_MOBILE_STYLES = {"fontSize": "var(--portal-text-lg,14px)"}
QUESTION_SUB_STYLES = {"margin": "0", "fontSize": "var(--portal-text-sm,12px)", "color": INK_SUBTLE, "lineHeight": "1.5"}

# What was answered two screens ago, on the screen that posts it, so a visitor does
# not have to walk back to remind themselves what they picked.
PICKED_ROW_STYLES = {"display": "flex", "flexWrap": "wrap", "gap": "8px", "padding": "14px 28px 0"}
PICKED_STYLES = {
	**ROW_FLEX,
	"gap": "6px",
	"padding": "5px 10px",
	"borderRadius": "999px",
	"background": SURFACE_HOVER,
	"fontSize": "var(--portal-text-xs,11px)",
	"fontWeight": "500",
	"color": INK_MUTED,
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
	"fontSize": "var(--portal-text-xs,11px)",
	"fontWeight": "600",
	"letterSpacing": "0.06em",
	"textTransform": "uppercase",
	"color": INK_FAINT,
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
	"fontSize": "var(--portal-text-md,13px)",
	"fontWeight": "600",
	"cursor": "pointer",
	"whiteSpace": "nowrap",
	"textDecoration": "none",
	"hover:filter": "brightness(1.35)",
}
WIZARD_GHOST_STYLES = {
	**WIZARD_BTN_STYLES,
	"background": SURFACE_CARD,
	"border": BORDER,
	"color": INK,
	"fontWeight": "500",
	"hover:filter": "none",
	"hover:borderColor": BORDER_STRONG,
}
GHOST_BTN_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"gap": "6px",
	"padding": "8px 14px",
	"borderRadius": "var(--brand-radius,8px)",
	"border": BORDER,
	"background": SURFACE_CARD,
	"color": INK,
	"fontFamily": "inherit",
	"fontSize": "var(--portal-text-md,13px)",
	"fontWeight": "500",
	"cursor": "pointer",
}
# "Send it again" is not a way forward, so it does not look like one.
LINK_BTN_STYLES = {
	"padding": "0",
	"border": "0",
	"background": "transparent",
	"color": INK_MUTED,
	"fontFamily": "inherit",
	"fontSize": "var(--portal-text-md,13px)",
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
	"background": SURFACE_SUNKEN,
}
NAV_END_STYLES = {**ROW_FLEX, "gap": "10px", "marginLeft": "auto"}
QUIET_NOTE_STYLES = {"fontSize": "var(--portal-text-xs,11px)", "color": INK_SUBTLE, "lineHeight": "1.5"}


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
	"background": SURFACE_CARD,
	"border": BORDER,
	"borderRadius": "var(--brand-radius,12px)",
	"fontFamily": "inherit",
	"color": INK,
	"cursor": "pointer",
	"hover:borderColor": BORDER_STRONG,
}
TILE_ICON_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"width": "40px",
	"height": "40px",
	"flexShrink": "0",
	"borderRadius": "10px",
	"background": SURFACE_HOVER,
	"color": INK_MUTED,
}
TILE_BODY_STYLES = {
	**COLUMN,
	"gap": "3px",
	"flex": "1 1 auto",
	"minWidth": "0",
	"alignItems": "flex-start",
}
TILE_LABEL_STYLES = {"fontSize": "var(--portal-text-md,13px)", "fontWeight": "600", "color": INK}
TILE_NOTE_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "color": INK_SUBTLE, "lineHeight": "1.45"}
TILE_META_STYLES = {**ROW_FLEX, "gap": "6px", "flexWrap": "wrap", "fontSize": "var(--portal-text-xs,11px)", "color": INK_SUBTLE}
TILE_RADIO_STYLES = {
	**ROW_FLEX,
	"justifyContent": "center",
	"width": "20px",
	"height": "20px",
	"flexShrink": "0",
	"borderRadius": "999px",
	"border": f"1px solid {BORDER_STRONG}",
	"background": SURFACE_CARD,
	"color": "var(--brand-primary-ink,#ffffff)",
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
				styles={**TABULAR, "fontSize": "var(--portal-text-md,13px)", "fontWeight": "600", "color": INK},
			),
			bound("span", "rate_note"),
		],
	)
	strong = {"fontWeight": "500", "color": INK_MUTED}
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
	"fontSize": "var(--portal-text-lg,14px)",
	"fontWeight": "600",
	"borderRadius": "var(--brand-radius,8px)",
	"border": BORDER,
	"background": SURFACE_CARD,
	"color": INK,
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
	"border": f"1px solid {OK_DEEP}",
	"borderRadius": "var(--brand-radius,12px)",
	"overflow": "hidden",
	"background": SURFACE_CARD,
}
OFFER_HEAD_STYLES = {**COLUMN, "gap": "3px", "padding": "18px 20px", "background": OK_SOFT}
OFFER_HEADLINE_STYLES = {"fontSize": "var(--portal-text-lg,14px)", "fontWeight": "600", "color": OK_DEEP}
OFFER_MESSAGE_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED, "lineHeight": "1.5"}
OFFER_GRID_STYLES = {
	"display": "grid",
	"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
	"borderTop": f"1px solid {OK_SOFT}",
}
OFFER_CELL_STYLES = {**COLUMN, "gap": "4px", "padding": "16px 20px"}
OFFER_LABEL_STYLES = {"fontSize": "var(--portal-text-xs,11px)", "color": INK_SUBTLE}
OFFER_VALUE_STYLES = {**TABULAR, "fontSize": "var(--portal-text-xl,17px)", "fontWeight": "600", "color": INK}
OFFER_FOOT_STYLES = {
	**ROW_FLEX,
	"gap": "12px",
	"flexWrap": "wrap",
	"padding": "14px 20px",
	"borderTop": BORDER,
	"background": SURFACE_SUNKEN,
}
REFERENCE_STYLES = {**TABULAR, "fontSize": "var(--portal-text-sm,12px)", "color": INK_MUTED}


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
	# Not on the scale: this is a glyph inside a fixed circle, so it may not grow.
	"fontSize": "10px",
	"fontWeight": "700",
}
TIMELINE_STEM_STYLES = {"width": "1px", "flex": "1 1 auto", "minHeight": "18px", "background": BORDER_COLOR}
TIMELINE_BODY_STYLES = {**COLUMN, "gap": "2px", "padding": "8px 0 14px"}
TIMELINE_TITLE_STYLES = {"fontSize": "var(--portal-text-md,13px)", "fontWeight": "500", "color": INK}
TIMELINE_NOTE_STYLES = {"fontSize": "var(--portal-text-sm,12px)", "color": INK_SUBTLE, "lineHeight": "1.5"}


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


def brand_lockup(word_styles, logo_styles=None, mark_styles=None, path=None):
	"""What a frame puts in its corner: the lender's logo, or the lender's name.

	Both are written into the page and one of them is dropped as it renders.
	build() writes the blocks once, while the logo is a setting read per request, so
	the choice cannot be made here; visibilityCondition is Builder's way of saying it
	in the page instead. brand_logo is the URL and is falsy when none is set, and
	show_wordmark is its negation, which the data layer has to supply because a
	condition cannot be inverted.

	`mark_styles` draws the generic glyph beside the name, for the bars that had one.
	It goes with the name: a lender that has given us its logo does not want ours
	next to it.
	"""
	image = block("img", styles=logo_styles or LOGO_STYLES, path=path and f"{path}/logo")
	# The src is a customAttribute rather than an attribute because create_html_tag
	# percent-encodes an img's src, which would turn the binding's own Jinja tag into
	# escape sequences. customAttributes are written to the tag verbatim.
	image["customAttributes"] = {"src": ""}
	image["visibilityCondition"] = "brand_logo"
	bind(image, "brand_logo", property="src", type="attribute")
	bind(image, "brand_name", property="alt", type="attribute")

	named = block(
		"div",
		path=path and f"{path}/name",
		styles={**ROW_FLEX, "gap": "10px", "minWidth": "0"},
		children=[
			*(
				[block("span", path=path and f"{path}/name/mark", styles=mark_styles, html=ICON_BRAND)]
				if mark_styles
				else []
			),
			bound("span", "brand_name", path=path and f"{path}/name/word", styles=word_styles),
		],
	)
	named["visibilityCondition"] = "show_wordmark"

	return [image, named]


def topbar(links):
	"""The brand, and the ways off this page.

	The last link is the way back in, which is the only thing anybody arrives in this
	bar looking for, so it is a pill rather than the third of three identical links.
	"""
	children = brand_lockup(
		{"fontSize": "var(--portal-text-md,13px)", "fontWeight": "500", "color": INK}, mark_styles=MARK_STYLES
	)

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
