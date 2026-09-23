# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The Statement of account and the Interest certificate, as Studio pages.

They replace two pages of the Builder portal this one was migrated from, and
read `get_statement_page` and `get_certificate_page` unchanged.

Neither wears a header button. The download lives inside the page, beside the dates or
the year it obeys: the Builder pages learnt that a button in the header had no access to
what was on screen, so it fetched the default period while the link below it followed
the picker.

The pickers themselves are new. The Builder pages took their period off the URL, because
a Builder page has no state; here the dates and the year are refs, and the data source
re-fetches when they change -- an API Resource's params are re-evaluated and reloaded on
every change to what they read.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	PANEL,
	block,
	button,
	card,
	column,
	container,
	fallback,
	heading,
	icon_line,
	icon_tile,
	muted,
	no_rows,
	reader,
	record_list,
	row,
	spacer,
	subject,
	text,
)
from lending.portal.studio_build.shell import frame

STATEMENT = "statement"
CERTIFICATE = "certificate"
ALERTS = ("alerts", "lending.portal.notifications.get_notifications")


def download(source, read, label=None):
	"""A button whose destination comes from the data, so it carries the period on screen."""
	return button(
		label or read("download_label"),
		script=f"window.open({source}.data.download_url, '_blank')",
		variant="solid",
	)


# --- statement of account -------------------------------------------------------------


def date_field(label, state):
	"""One end of the period. Not clearable: an empty date falls back to the endpoint's
	default, and the picker would then show nothing while the page shows a period."""
	return block(
		"FormControl",
		props={
			"type": "date",
			"label": label,
			"clearable": False,
			# dayjs tokens: the date as the ledger below prints it, not the ISO the ref holds.
			"format": "DD MMM YYYY",
			"modelValue": {"$type": "variable", "name": state},
		},
		styles={"width": "172px"},
	)


# The ranges a borrower asks their lender for, one press each. The year is the Indian
# financial year, April to March, as it is in `lending.portal.statement`.
PERIODS = (("This FY", "this_year"), ("Last FY", "last_year"), ("Last 3 months", "last_quarter"))


def period_bar(read):
	"""The filter row of a desk report: the dates, a few ranges, and the download at the end.

	The download sits here rather than in the header because it obeys these dates --
	its link comes from the payload, which the dates re-fetch.
	"""
	ranges = row(
		[button(label, script=f"setPeriod('{period}')") for label, period in PERIODS],
		gap="6px",
	)
	fields = row(
		[date_field("From", "fromDate"), date_field("To", "toDate"), ranges],
		gap="12px",
		align="end",
		styles={"flexWrap": "wrap"},
	)

	return row(
		[fields, spacer(), download(STATEMENT, read)],
		gap="12px",
		align="end",
		styles=dict(PANEL, flexWrap="wrap"),
	)


def figure_card(title, value, note, glyph, theme, **kwargs):
	"""One total, led by a tile the way the overview's figure cards are."""
	lines = column(
		[
			text(title, size="text-sm", styles={"color": "var(--ink-gray-6)"}),
			text(value, tag="div", size="text-xl", styles=FIGURE),
			muted(note),
		],
		gap="4px",
		styles={"minWidth": "0px"},
	)

	return row(
		[icon_tile(glyph, theme), lines],
		gap="12px",
		align="start",
		styles=dict(PANEL, flex="1 1 220px"),
		**kwargs,
	)


def figure_strip(cards):
	"""Figure cards in a row, wrapping by their own width -- see loan_pages.TermCell."""
	return container(cards, styles={"display": "flex", "flexWrap": "wrap", "gap": "16px", "width": "100%"})


# Figures set in tabular digits, so a column of them lines up digit under digit.
FIGURE = {"fontWeight": "600", "fontVariantNumeric": "tabular-nums", "color": "var(--ink-gray-9)"}
AMOUNT = {"fontVariantNumeric": "tabular-nums", "whiteSpace": "nowrap"}

# The rows' share of the 12px inset the column names take from LIST_INSET. The published
# bundle drops a ListRow's own styles (see blocks.ROW_PADDING), and frappe-ui sets this
# variable only on a row that can be clicked -- so a ledger's rows ran 12px wider than
# their header on each side, and every column but the first and last drifted off its name.
ROW_INSET = {"--_list-row-pad": "12px"}


def summary_strip(read):
	"""Charged, paid and what is left."""
	return figure_strip(
		[
			figure_card(
				"Charged", read("summary.charged"), "Disbursements, interest and charges", "arrow-up", "orange"
			),
			figure_card("Paid", read("summary.paid"), "Repayments received", "arrow-down", "green"),
			figure_card(
				"Closing balance", read("summary.balance"), read("summary.balance_note"), "wallet", "blue"
			),
		]
	)


def ledger(read):
	"""The entries as a ledger: debit and credit in columns of their own, then the balance.

	It keeps a minimum width and scrolls inside its card on a phone, as the desk's report
	view does, rather than folding five columns into a stack nobody can read across.
	"""
	amount = {"size": "text-base", "styles": AMOUNT}
	table = record_list(
		[
			("minmax(96px, 0.8fr)", "Date"),
			("minmax(0, 2fr)", "Particulars"),
			("minmax(0, 1fr)", "Debit", "end"),
			("minmax(0, 1fr)", "Credit", "end"),
			("minmax(0, 1fr)", "Balance", "end"),
		],
		read("rows"),
		[
			[text("{{ item.date }}", size="text-base", styles={"color": "var(--ink-gray-7)", "whiteSpace": "nowrap"})],
			[subject("{{ item.label }}"), muted("{{ item.detail }}", visible="{{ item.detail }}")],
			[text("{{ item.debit }}", **amount)],
			[text("{{ item.credit }}", **amount)],
			[text("{{ item.balance }}", size="text-base", styles=dict(AMOUNT, fontWeight="500"))],
		],
	)
	table["baseStyles"].update(ROW_INSET, minWidth="640px")

	return container([table], styles={"overflowX": "auto"})


def ledger_empty(read):
	"""A period with nothing in it says so, and says what to try."""
	return column(
		[
			icon_tile("file", "gray", styles={"marginBottom": "8px"}),
			text("No transactions in this period", size="text-base", styles={"fontWeight": "600"}),
			muted("Pick a wider range above to see earlier entries.", styles={"textAlign": "center"}),
		],
		gap="4px",
		visible=no_rows(read("rows")),
		styles={"alignItems": "center", "padding": "32px 16px"},
	)


def statement_content(read):
	return [
		period_bar(read),
		summary_strip(read),
		card("Transactions", read("rows_note"), column([ledger(read), ledger_empty(read)], gap="0px")),
	]


# The dates start on the period the endpoint would default to, so the pickers show the
# period on screen rather than "Select date". Function declarations, because the refs
# that call them are declared above this in the module.
STATEMENT_SCRIPT = """\
\tfunction isoDay(day: Date) {
\t\tconst pad = (n: number) => String(n).padStart(2, "0")
\t\treturn `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`
\t}

\tfunction yearStart(yearsBack = 0) {
\t\tconst today = new Date()
\t\tconst start = today.getFullYear() - (today.getMonth() < 3 ? 1 : 0) - yearsBack
\t\treturn new Date(start, 3, 1)
\t}

\tconst setPeriod = (period: string) => {
\t\tconst today = new Date()
\t\tif (period === "last_year") {
\t\t\tconst start = yearStart(1)
\t\t\tfromDate.value = isoDay(start)
\t\t\ttoDate.value = isoDay(new Date(start.getFullYear() + 1, 2, 31))
\t\t} else if (period === "last_quarter") {
\t\t\tfromDate.value = isoDay(new Date(today.getFullYear(), today.getMonth() - 3, today.getDate()))
\t\t\ttoDate.value = isoDay(today)
\t\t} else {
\t\t\tfromDate.value = isoDay(yearStart())
\t\t\ttoDate.value = isoDay(today)
\t\t}
\t}"""


def build_statement():
	read = reader(STATEMENT)

	return upsert_page(
		"Statement of account",
		"/statement",
		frame(STATEMENT, statement_content(read)),
		[
			api_resource(
				STATEMENT,
				"lending.portal.statement.get_statement_page",
				params={"from_date": "{{ fromDate }}", "to_date": "{{ toDate }}"},
			),
			api_resource(*ALERTS, auto=0),
		],
		script=page_script(
			state=[("fromDate", "isoDay(yearStart())"), ("toDate", "isoDay(new Date())")],
			body=STATEMENT_SCRIPT,
			returns=["setPeriod"],
		),
	)


# --- interest certificate ---------------------------------------------------------------


def year_picker(read):
	"""Unlabelled: the heading beside it already names the year it holds."""
	return block(
		"FormControl",
		props={
			"type": "select",
			"options": fallback(read("years"), "[]"),
			"modelValue": {"$type": "variable", "name": "year"},
		},
		styles={"width": "140px"},
	)


def year_head(read):
	"""The certificate's own head, the way a desk form carries its title: the year and
	whether it has closed on the left, the picker and the download on the right.

	The line under the title says what "provisional" or "final" means for the figures.
	"""
	kind = block(
		"Badge",
		props={"label": read("kind"), "theme": read("kind_theme"), "variant": "subtle", "size": "md"},
	)
	title = column(
		[row([heading(read("year_label")), kind], gap="8px"), muted(read("rows_note"))],
		gap="4px",
		styles={"minWidth": "0px"},
	)
	# The heading already names the year, so the button need not, and fits a phone.
	controls = row(
		[year_picker(read), download(CERTIFICATE, read, "Download certificate")],
		gap="8px",
		styles={"flexWrap": "wrap"},
	)

	return row([title, spacer(), controls], gap="16px", styles={"flexWrap": "wrap"})


# The inset each figure keeps from the rule on its left, as field_grid does.
FIGURE_INSET = 20


def figure_cell(title, value, note, **kwargs):
	"""One figure of the summary: a grey label, the amount, and what it counts."""
	return column(
		[
			text(title, size="text-sm", styles={"color": "var(--ink-gray-5)"}),
			text(value, tag="div", size="text-2xl", styles=FIGURE),
			muted(note),
		],
		gap="4px",
		styles={
			"minWidth": "0px",
			"paddingInlineStart": f"{FIGURE_INSET}px",
			"paddingInlineEnd": f"{FIGURE_INSET}px",
			"borderInlineStart": "1px solid var(--outline-gray-1)",
		},
		**kwargs,
	)


def paid_summary(read):
	"""The year's figures in one panel, split by rules rather than boxed apart.

	Interest first: it is the figure the certificate exists to state. The grid is pulled
	left by one inset and one rule, and the panel clips it, so whichever figure starts a
	line -- at any width the grid wraps to -- has no rule before it.
	"""
	grid = container(
		[
			figure_cell("Interest paid", read("summary.interest"), "On your loans this year"),
			figure_cell("Principal repaid", read("summary.principal"), "Towards the amount borrowed"),
			figure_cell(
				"Penalty and charges",
				read("summary.other"),
				"Late fees and other charges",
				visible=read("summary.other"),
			),
			figure_cell("Total paid", read("summary.total"), "Interest, principal and charges"),
		],
		styles={
			"display": "grid",
			"gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
			"rowGap": "20px",
			"marginInlineStart": f"-{FIGURE_INSET + 1}px",
		},
	)

	return container([grid], styles=dict(PANEL, overflow="hidden", padding="20px"))


def disclaimer(read):
	"""A footnote to the figures, not a banner: part of what they mean, never dismissed."""
	return icon_line(
		"info",
		read("disclaimer"),
		visible=read("disclaimer"),
		styles={"paddingTop": "12px", "borderTop": "1px solid var(--outline-gray-1)"},
	)


def accounts_table(read):
	"""Each loan's share of the year, so a borrower with two loans can file them apart."""
	amount = {"size": "text-base", "styles": AMOUNT}
	table = record_list(
		[
			("minmax(0, 2fr)", "Loan"),
			("minmax(0, 1fr)", "Interest", "end"),
			("minmax(0, 1fr)", "Principal", "end"),
			("minmax(0, 1fr)", "Total", "end"),
		],
		read("accounts"),
		[
			[subject("{{ item.label }}"), muted("{{ item.value }}")],
			[text("{{ item.interest }}", **amount)],
			[text("{{ item.principal }}", **amount)],
			[text("{{ item.total }}", size="text-base", styles=dict(AMOUNT, fontWeight="500"))],
		],
	)
	table["baseStyles"].update(ROW_INSET, minWidth="520px")

	return container([table], styles={"overflowX": "auto"})


def certificate_content(read):
	return [
		year_head(read),
		paid_summary(read),
		card(
			"Accounts covered",
			read("accounts_note"),
			column([accounts_table(read), disclaimer(read)], gap="12px"),
		),
	]


# The year starts on the current one, so the picker shows it rather than "Select option".
CERTIFICATE_SCRIPT = """\
\tfunction currentYear() {
\t\tconst today = new Date()
\t\tconst start = today.getFullYear() - (today.getMonth() < 3 ? 1 : 0)
\t\treturn `${start}-${start + 1}`
\t}"""


def build_certificate():
	read = reader(CERTIFICATE)

	return upsert_page(
		"Interest certificate",
		"/certificate",
		frame(CERTIFICATE, certificate_content(read)),
		[
			api_resource(
				CERTIFICATE,
				"lending.portal.statement.get_certificate_page",
				params={"year": "{{ year }}"},
			),
			api_resource(*ALERTS, auto=0),
		],
		script=page_script(state=[("year", "currentYear()")], body=CERTIFICATE_SCRIPT),
	)


def build():
	return build_statement(), build_certificate()
