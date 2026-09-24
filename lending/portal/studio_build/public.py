# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The frame the two public pages share.

Neither /apply nor /track wears the borrower frame. Every row in that sidebar needs a
login, so a guest clicking one would be bounced; they carry this top bar instead, which
is why it is here rather than in `shell`.

Both pages are published with `allow_guest`, which is what lets the app renderer serve
them to somebody who has not signed in -- and, because one published guest page makes
the whole app guest-renderable, what lets the router reach them at all.
"""

from lending.portal.studio_build.blocks import (
	block,
	brand_style,
	button,
	container,
	icon,
	root,
	row,
	slot,
	spacer,
	text,
)

MARK = {"width": "36px", "height": "36px", "flexShrink": "0", "borderRadius": "8px"}

# Routes the site serves rather than the app. The rest are the app's own, and go through
# its router: a bare /track is the Builder page, which is not this portal.
SITE_ROUTES = {"/login"}


def page(read, links, body, width="720px"):
	"""A public page: the bar, then one column of content, centred and capped at `width`."""
	well = container(
		body,
		styles={
			"display": "flex",
			"flexDirection": "column",
			"gap": "16px",
			# Shorter windows give up the padding first, before anything has to scroll.
			"padding": "clamp(16px, 3.6vh, 40px) 20px",
			"width": "100%",
			"maxWidth": width,
			"margin": "0 auto",
			# Fills the height under the bar, so a page can centre itself in what is left.
			"flex": "1 0 auto",
		},
		mobile={"padding": "24px 16px"},
	)

	return root(
		[
			container(
				[top_bar(read, links), well],
				styles={
					"display": "flex",
					"flexDirection": "column",
					"width": "100%",
					"height": "100%",
					"overflowY": "auto",
					# A step off white, so the panels on it read as panels.
					"backgroundColor": "var(--surface-gray-1)",
				},
			),
			brand_style(read("brand_style")),
		],
		direction="column",
	)


def mark(read):
	"""The lender's logo, or the first letter of its name on a tile when it has none.

	Both are written out and one renders, for the reason `shell.brand` gives: the page is
	built once and Lending Settings is read per request.
	"""
	logo = block(
		"ImageView",
		props={"image": read("brand_logo"), "alt": "", "shape": "square", "size": "lg"},
		styles=dict(MARK, overflow="hidden"),
		visible=read("brand_logo"),
	)
	letter = text(
		"{{ (%s || '').charAt(0) }}" % read("brand_name")[2:-2].strip(),
		size="text-lg",
		styles=dict(
			MARK,
			display="flex",
			alignItems="center",
			justifyContent="center",
			fontWeight="600",
			textTransform="uppercase",
			# Inverted, because the bar behind it is already the primary.
			backgroundColor="var(--portal-primary-ink, var(--surface-gray-2))",
			color="var(--portal-primary, var(--ink-gray-8))",
		),
		visible=read("show_wordmark"),
	)

	return [logo, letter]


def link_button(label, href, glyph=None, variant="ghost"):
	"""One place in the bar, led by `glyph` when it has one.

	The label goes in the default slot as well as the prop: once a block has any slot,
	Studio hands Button an empty default one too, and Button renders that over `label`.
	"""
	slots = {}
	if glyph:
		slots = {
			**slot("prefix", [icon(glyph, size=16)]),
			**slot("default", [text(label, tag="span", size="text-base")]),
		}

	go = f"window.location.href = '{href}'" if href in SITE_ROUTES else f"open('{href}')"

	return button(
		label,
		script=go,
		variant=variant,
		props={"size": "md"},
		slots=slots,
	)


def top_bar(read, links):
	"""The lender's name, and the two other places a visitor might want to be.

	A link is (label, href) or (label, href, glyph). The last one is the one a returning
	borrower wants, so it is the one drawn as a solid button rather than as a bare label:
	an outline's grey rule is lost on the primary, and a solid one on the band wears the
	action colour the signed-in header's button does.
	"""
	return row(
		[
			*mark(read),
			text(
				read("brand_name"),
				tag="span",
				size="text-lg",
				styles={"fontWeight": "600", "whiteSpace": "nowrap", "color": "var(--ink-gray-9)"},
				mobile={"display": "none"},
			),
			spacer(),
			*[
				link_button(*link, variant="solid" if index == len(links) - 1 else "ghost")
				for index, link in enumerate(links)
			],
		],
		gap="12px",
		# Painted in the lender's primary colour, as the signed-in header is; the class
		# also turns the greys the bar's text and buttons use into the band's own ink.
		classes=["portal-header"],
		styles={
			"padding": "10px 32px",
			"flexShrink": "0",
			"width": "100%",
			"borderWidth": "0px 0px 1px 0px",
			"borderStyle": "solid",
			"borderColor": "var(--portal-primary, var(--outline-gray-2))",
			"backgroundColor": "var(--portal-primary, var(--surface-base))",
		},
		mobile={"padding": "12px 16px", "gap": "4px"},
	)
