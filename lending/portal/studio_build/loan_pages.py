# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower's Loan accounts list, and one loan's detail page.

Both replace pages of the Builder portal this one was migrated from, and read the
endpoints those pages read.

The detail page's route carries the loan name. Builder marked a route dynamic with
angle brackets and frappe's router put the match in `frappe.form_dict`; Studio's router
is vue-router, so the segment is `:name` and the page hands it to the endpoint as a
request parameter. `get_loan_detail` reads it from `form_dict` either way, and proves
the borrower owns the loan before reading further.
"""

from lending.portal.studio_build.app import api_resource, upsert_page
from lending.portal.studio_build.blocks import (
	button,
	card,
	column,
	muted,
	pair_grid,
	pair_rows,
	reader,
	record_list,
	repeater,
	row,
	spacer,
	stat,
	stat_strip,
	text,
	toned_badge,
	two_columns,
)
from lending.portal.studio_build.shell import frame

LIST_SOURCE = "loans"
DETAIL_SOURCE = "loan"
ALERTS = ("alerts", "lending.portal.notifications.get_notifications")


# --- the list -----------------------------------------------------------------------


def accounts(read):
	"""Each row is a link, so the whole line opens that loan rather than a stray word."""
	return record_list(
		[
			("minmax(0, 1fr)", "Account"),
			("9rem", "Status"),
			("10rem", "Next repayment"),
			("10rem", "Outstanding"),
		],
		read("accounts"),
		[
			[text("{{ item.product }}", size="text-base"), muted("{{ item.terms }}")],
			[toned_badge("{{ item.status_label }}", "item.tone")],
			[text("{{ item.next_date }}", size="text-base"), muted("{{ item.next_amount }}")],
			[text("{{ item.outstanding }}", size="text-base"), muted("{{ item.against }}")],
		],
		script="open(item.url)",
	)


def list_content(read):
	return [
		stat_strip(
			[
				stat(
					read("label_next"),
					read("next_amount"),
					read("next_note"),
					flag=read("next_flag"),
				),
				stat(read("label_outstanding"), read("outstanding"), read("outstanding_note")),
				stat(read("label_sanctioned"), read("sanctioned"), read("sanctioned_note")),
			]
		),
		card("Loan accounts", read("accounts_note"), accounts(read)),
	]


def build_list():
	read = reader(LIST_SOURCE)

	return upsert_page(
		"Loan accounts",
		"/loans",
		frame(
			LIST_SOURCE,
			list_content(read),
			action_label="Apply for a loan",
			action_route="/apply",
		),
		[
			api_resource(LIST_SOURCE, "lending.portal.loans.get_loans_page"),
			api_resource(*ALERTS, auto=0),
		],
	)


# --- one loan -----------------------------------------------------------------------


def schedule(read):
	"""Every instalment, what it is for, and whether it has been met."""
	return record_list(
		[("minmax(0, 1fr)", "Instalment"), ("8rem", "State"), ("10rem", "Amount")],
		read("schedule"),
		[
			[text("{{ item.detail }}", size="text-base"), muted("{{ item.balance }}")],
			[toned_badge("{{ item.state }}", "item.state_tone")],
			[text("{{ item.amount }}", size="text-base"), muted("{{ item.date }}")],
		],
	)


def disbursements(read):
	"""No link on these rows: this is already the loan they would open."""
	entry = row(
		[
			column(
				[text("{{ dataItem.detail }}", size="text-base"), muted("{{ dataItem.running }}")],
				gap="2px",
			),
			spacer(),
			text("{{ dataItem.amount }}", size="text-base"),
		],
		gap="10px",
		styles={"padding": "8px 0"},
	)

	return repeater(read("disbursements"), entry, empty="Nothing drawn yet")


def payoff(read):
	"""The figure, and a request. PORTAL_PLAN.md section 6.11 takes no money here."""
	return column(
		[
			pair_rows(read("payoff")),
			button(
				"Request closure",
				script="toast.success('We will be in touch about closing this loan.')",
			),
		],
		gap="10px",
	)


def detail_content(read):
	return [
		card("Loan details", read("summary_note"), pair_grid(read("summary"))),
		two_columns(
			[
				card("Repayment schedule", read("schedule_note"), schedule(read)),
				card("Disbursements", read("disbursements_note"), disbursements(read)),
			],
			[
				card("Payoff amount", read("payoff_note"), payoff(read)),
				card("Charges", read("charges_note"), pair_rows(read("charges"))),
			],
		),
	]


def build_detail():
	read = reader(DETAIL_SOURCE)

	return upsert_page(
		"Loan",
		"/loan/:name",
		frame(
			DETAIL_SOURCE,
			detail_content(read),
			action_label="Download statement",
			action_route="/borrower/statement",
		),
		[
			api_resource(
				DETAIL_SOURCE,
				"lending.portal.loans.get_loan_detail",
				params={"name": "{{ route.params.name }}"},
			),
			api_resource(*ALERTS, auto=0),
		],
	)


def build():
	return build_list(), build_detail()
