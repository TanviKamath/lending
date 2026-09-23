# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""One loan's detail page, served at two routes.

The sidebar's Loan account row opens `/loans`, which names no loan: the endpoint picks
the borrower's main one. There is no list of loans in between. `/loan/:name` is the same
page for one named loan, which is where the overview, search and notifications link.

The named route carries the loan name. Builder marked a route dynamic with
angle brackets and frappe's router put the match in `frappe.form_dict`; Studio's router
is vue-router, so the segment is `:name` and the page hands it to the endpoint as a
request parameter. `get_loan_detail` reads it from `form_dict` either way, and proves
the borrower owns the loan before reading further.
"""

from lending.portal.studio_build.app import api_resource, upsert_page
from lending.portal.studio_build.blocks import (
	PANEL,
	any_row,
	button,
	column,
	container,
	divider,
	heading,
	icon,
	icon_tile,
	muted,
	no_rows,
	reader,
	repeater,
	row,
	spacer,
	subject,
	text,
)
from lending.portal.studio_build.shell import frame

DETAIL_SOURCE = "loan"
ALERTS = ("alerts", "lending.portal.notifications.get_notifications")


def terms_card(read):
	"""The loan's terms as two rows of four figures, split by rules.

	Not `card()`: this one leads with a tile. The
	cells are placed by hand rather than repeated, because each one is a little
	different -- a frequency under the instalment, a hint on the total, a calendar on the date.
	"""
	term = TermCell(read)
	head = row(
		[
			icon_tile("file-text", "blue"),
			column([heading("Loan details"), muted(read("summary_note"))], gap="2px"),
		],
		gap="12px",
		align="start",
	)
	figures = column(
		[
			term.row(
				term("Loan amount (sanctioned)", "sanctioned"),
				term("Disbursed amount", "disbursed"),
				term("Interest rate (p.a.)", "rate"),
				term("Tenure", "tenure"),
			),
			divider(),
			term.row(
				term("EMI amount", "instalment", note="frequency"),
				term("Total repayable", "total", hint="Principal plus all interest over the tenure"),
				term("Paid so far", "paid", note="written_off"),
				term("First due date", "first_due", glyph="calendar"),
			),
		],
		gap="16px",
		visible=read("terms"),
	)

	return column([head, figures], gap="20px", styles=dict(PANEL, padding="20px"))


class TermCell:
	"""One figure in the terms card, and the rules that keep four of them apart.

	Four figures wrap to two, then one, by the card's own width rather than a
	breakpoint: Studio's tablet styles start below a 768px viewport, but the sidebar
	squeezes the card well above that. So a row is two pairs in a wrapping flex, and
	each pair wraps its own two cells.

	A rule is every cell's left border. The row is pulled left by one rule and one
	gutter inside a clipping box, so whichever cell starts a line has its rule cut off
	and its text lines up with the heading.
	"""

	GUTTER = 20

	def __init__(self, read):
		self.read = read

	def __call__(self, label, key, note=None, hint=None, glyph=None):
		return column(
			[self.label(label, hint), self.value(key, glyph), *self.note(note)],
			gap="4px",
			styles={
				"flex": "1 1 190px",
				"minWidth": "0px",
				"paddingInline": f"{self.GUTTER}px",
				"borderInlineStartWidth": "1px",
				"borderInlineStartStyle": "solid",
				"borderInlineStartColor": "var(--outline-gray-2)",
			},
		)

	def row(self, first, second, third, fourth):
		line = {"display": "flex", "flexWrap": "wrap", "rowGap": "16px"}
		pairs = [
			container(cells, styles=dict(line, flex="1 1 380px"))
			for cells in ([first, second], [third, fourth])
		]
		pulled = container(pairs, styles=dict(line, marginInlineStart=f"-{self.GUTTER + 1}px"))

		# `overflow: hidden` drops a flex item's minimum height to zero, and the page's
		# column then squeezes the row to nothing. It must not shrink.
		return container([pulled], styles={"overflow": "hidden", "flexShrink": "0"})

	def label(self, label, hint):
		words = text(label, size="text-sm", styles={"color": "var(--ink-gray-6)"})
		if not hint:
			return words

		mark = icon("info", size=14, hint=hint, styles={"color": "var(--ink-gray-5)", "cursor": "help"})
		return row([words, mark], gap="4px")

	def value(self, key, glyph):
		figure = text(
			self.read(f"terms.{key}"),
			tag="div",
			size="text-xl",
			styles={"fontWeight": "600", "fontVariantNumeric": "tabular-nums"},
		)
		if not glyph:
			return figure

		return row([icon(glyph, size=18, styles={"color": "var(--ink-gray-5)"}), figure], gap="8px")

	def note(self, key):
		if not key:
			return []

		expression = self.read(f"terms.{key}")
		return [muted(expression, visible=expression)]


def payoff_card(read):
	"""The figure, and a request. PORTAL_PLAN.md section 6.11 takes no money here.

	Not `card()`: it leads with a tile, and the figure sits on a green panel of its
	own. The sizes and gaps are measured off the design this card was drawn from,
	which sets its type tighter than frappe-ui's -- hence the letter spacing written
	out on the title, the subtitle and the figure.
	"""
	head = half_head(
		container([text("₹", tag="div", size="text-2xl", styles=RUPEE)], styles=round_tile("green")),
		"Payoff amount",
		"Total amount required to close this loan.",
	)
	figure = column(
		[
			text("Outstanding amount", size="text-sm", styles={"color": "var(--ink-gray-8)"}),
			text(read("payoff_total"), tag="div", size="text-3xl", styles=PAYOFF_FIGURE),
			text(read("payoff_note"), size="text-sm", styles={"marginTop": "4px", "color": "var(--ink-gray-5)"}),
		],
		gap="0px",
		styles={
			"padding": "20px 22px 18px",
			"borderRadius": "var(--radius-5)",
			"backgroundColor": "var(--surface-green-1)",
		},
	)
	request = button(
		"Request closure",
		script="toast.success('We will be in touch about closing this loan.')",
		props={"size": "md"},
		styles={"width": "100%", "height": "34px", "fontSize": "13px"},
	)

	return column([head, figure, request], gap="20px", styles=HALF_PANEL)


def charges_card(read):
	"""What the loan carries besides principal and interest, or a word that it carries none.

	Drawn to the payoff card's measure, since the two stand side by side: the same
	round tile, the same heading, the same panel. The subtitle says what the card
	is for rather than how many rows it holds -- the rows say that themselves, and an
	empty card says it in its own words below.
	"""
	charges = read("charges")
	head = half_head(
		icon("file-text", size=22, styles=dict(round_tile("purple"), color="var(--ink-purple-7)")),
		"Charges",
		"Additional charges applicable on this loan.",
	)
	entry = row(
		[
			column(
				[
					subject("{{ dataItem.label }}"),
					muted("{{ dataItem.detail }}", visible="{{ dataItem.detail }}"),
				],
				gap="2px",
				styles={"minWidth": "0px"},
			),
			spacer(),
			text(
				"{{ dataItem.value }}",
				size="text-base",
				styles={"fontWeight": "600", "fontVariantNumeric": "tabular-nums", "whiteSpace": "nowrap"},
			),
		],
		gap="12px",
		styles={"padding": "10px 0"},
	)
	listed = repeater(
		charges,
		entry,
		visible=any_row(charges),
		styles={
			"padding": "6px 18px",
			"borderRadius": "var(--radius-5)",
			"backgroundColor": "var(--surface-gray-1)",
		},
	)

	return column([head, listed, charges_empty(charges)], gap="20px", styles=HALF_PANEL)


def charges_empty(charges):
	"""A loan with no charges is the usual case, so its card says so calmly and centred.

	It grows into whatever height the payoff card beside it sets, and centres in that.
	"""
	return column(
		[
			icon(
				"file",
				size=22,
				styles=dict(round_tile("gray"), color="var(--ink-gray-6)", marginBottom="10px"),
			),
			text(
				"No charges on this loan",
				size="text-base",
				styles={"fontWeight": "600", "color": "var(--ink-gray-8)"},
			),
			muted("Any processing fees or other charges will appear here.", styles={"textAlign": "center"}),
		],
		gap="4px",
		visible=no_rows(charges),
		styles={"flex": "1 1 auto", "alignItems": "center", "justifyContent": "center", "padding": "12px 16px 16px"},
	)


def half_head(tile, title, subtitle):
	"""The round tile and two lines that lead each of the two half-width cards."""
	return row(
		[
			tile,
			column(
				[
					heading(title, size="text-lg", styles={"letterSpacing": "0"}),
					muted(subtitle, styles={"letterSpacing": "0"}),
				],
				gap="6px",
			),
		],
		gap="20px",
	)


def round_tile(theme):
	"""A disc rather than icon_tile's square: the design this column was drawn from rounds it."""
	return {
		"display": "flex",
		"alignItems": "center",
		"justifyContent": "center",
		"flex": "0 0 auto",
		"width": "48px",
		"height": "48px",
		"borderRadius": "var(--radius-full)",
		"backgroundColor": f"var(--surface-{theme}-1)",
	}


HALF_PANEL = dict(PANEL, padding="22px", borderRadius="var(--radius-5)", flex="1 1 auto")

# The payoff tile's glyph is type rather than a lucide icon: the design draws the rupee
# in the face of the figure beside it, not as a stroked outline.
RUPEE = {
	"fontSize": "27px",
	"fontWeight": "500",
	"lineHeight": "1",
	"letterSpacing": "0",
	"color": "var(--ink-green-8)",
}
# Inter's display cut, which is narrower than the text cut frappe-ui sets everywhere
# else: at this size the text cut ran the figure a tenth wider than the design.
PAYOFF_FIGURE = {
	"marginTop": "6px",
	"fontSize": "27px",
	"fontWeight": "600",
	"letterSpacing": "-0.02em",
	"fontVariationSettings": "'opsz' 32, 'cv11' 1",
	"color": "var(--ink-gray-9)",
}


def detail_content(read):
	"""The terms, then what closing the loan takes beside what it carries."""
	return [
		terms_card(read),
		side_by_side((payoff_card(read), "1 1 320px"), (charges_card(read), "1 1 320px")),
	]


def side_by_side(*cells):
	"""Cards of one height in a row, each stacking under the last once it would go narrower
	than its basis.

	Wrapped by each card's own width rather than a breakpoint, for the reason
	`TermCell` gives: the sidebar squeezes the page well above Studio's tablet width,
	where `two_columns` would still hold both cards side by side.

	Each card sits in a column cell of its own, which stretches it to the cell's width;
	a card that also grows (`HALF_PANEL`) fills the cell's height, so that it matches
	its neighbour's.
	"""
	cell = {"display": "flex", "flexDirection": "column", "minWidth": "0px"}

	return container(
		[container([card], styles=dict(cell, flex=flex)) for card, flex in cells],
		styles={"display": "flex", "flexWrap": "wrap", "gap": "16px", "width": "100%"},
	)


def build_detail(title, route, params=None):
	read = reader(DETAIL_SOURCE)

	return upsert_page(
		title,
		route,
		frame(
			DETAIL_SOURCE,
			detail_content(read),
		),
		[
			api_resource(DETAIL_SOURCE, "lending.portal.loans.get_loan_detail", params=params),
			api_resource(*ALERTS, auto=0),
		],
	)


def build():
	return (
		build_detail("Loan account", "/loans"),
		build_detail("Loan", "/loan/:name", params={"name": "{{ route.params.name }}"}),
	)
