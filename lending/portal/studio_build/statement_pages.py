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
	alert,
	block,
	button,
	card,
	column,
	pair_rows,
	reader,
	row,
)
from lending.portal.studio_build.shell import frame

STATEMENT = "statement"
CERTIFICATE = "certificate"
ALERTS = ("alerts", "lending.portal.notifications.get_notifications")


def download(source, read):
	"""A button whose destination comes from the data, so it carries the period on screen."""
	return button(
		read("download_label"),
		script=f"window.open({source}.data.download_url, '_blank')",
		variant="solid",
	)


# --- statement of account -------------------------------------------------------------


def statement_dates():
	"""The period on screen. Changing either date re-fetches the source."""
	return row(
		[
			block(
				"FormControl",
				props={
					"type": "date",
					"label": "From",
					"modelValue": {"$type": "variable", "name": "fromDate"},
				},
			),
			block(
				"FormControl",
				props={
					"type": "date",
					"label": "To",
					"modelValue": {"$type": "variable", "name": "toDate"},
				},
			),
		],
		gap="12px",
		align="end",
	)


def statement_content(read):
	return [
		card("Period", "", statement_dates()),
		card("Summary", read("totals_note"), column([pair_rows(read("totals")), download(STATEMENT, read)], gap="12px")),
		card("Entries", read("rows_note"), pair_rows(read("rows"), with_detail=True)),
	]


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
		script=page_script(state=[("fromDate", '""'), ("toDate", '""')]),
	)


# --- interest certificate ---------------------------------------------------------------


def year_picker(read):
	return block(
		"FormControl",
		props={
			"type": "select",
			"label": "Financial year",
			"options": read("years"),
			"modelValue": {"$type": "variable", "name": "year"},
		},
	)


def certificate_content(read):
	return [
		card(read("year_label"), read("head_note"), year_picker(read)),
		card("Amounts paid", read("rows_note"), column([pair_rows(read("rows")), download(CERTIFICATE, read)], gap="12px")),
		alert(read("disclaimer"), theme="yellow"),
		card("Accounts covered", read("accounts_note"), pair_rows(read("accounts"), with_detail=True)),
	]


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
		script=page_script(state=[("year", '""')]),
	)


def build():
	return build_statement(), build_certificate()
