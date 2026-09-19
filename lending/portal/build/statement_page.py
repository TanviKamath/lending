# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Statement of account page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.statement_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import card, download_link, pair_rows

PAGE_NAME = "Borrower Statement"
ROUTE = "borrower/statement"
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal.statement.get_statement_page"))  # noqa: F821
'''


def content():
	return [
		card("Summary", "totals_note", pair_rows("totals")),
		download_link("download_url", "download_label"),
		card("Entries", "rows_note", pair_rows("rows", with_detail=True)),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Statement of account",
		content(),
		# The header button has no access to the page's filters, so it downloads the
		# default period. The link inside the page carries whatever is on screen.
		action_href="/api/method/lending.portal.downloads.download_statement",
		data_script=DATA_SCRIPT,
	)
