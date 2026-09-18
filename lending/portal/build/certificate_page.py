# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Interest certificate page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.certificate_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import card, download_link, note_panel, pair_rows

PAGE_NAME = "Borrower Interest Certificate"
ROUTE = "borrower/certificate"
NAV_HREF = "/borrower/certificate"
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal.statement.get_certificate_page"))  # noqa: F821
'''


def content():
	return [
		card("Amounts paid", "rows_note", pair_rows("rows")),
		download_link("download_url", "download_label"),
		note_panel("disclaimer"),
		card("Accounts covered", "accounts_note", pair_rows("accounts", with_detail=True)),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Interest certificate",
		NAV_HREF,
		content(),
		action_href="/api/method/lending.portal.downloads.download_certificate",
		data_script=DATA_SCRIPT,
	)
