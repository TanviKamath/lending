# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Documents page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal_documents_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see portal_shell.
"""

from lending.portal_shell import build_page
from lending.portal_theme import card, note_panel, pair_rows

PAGE_NAME = "Borrower Documents"
ROUTE = "borrower/documents"
NAV_HREF = "/borrower/documents"
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal_applications.get_documents_page"))  # noqa: F821
'''


def content():
	return [
		card("Documents you have sent", "documents_note", pair_rows("documents", with_detail=True, marker=True)),
		note_panel("upload_note"),
		card("Applications", "applications_note", pair_rows("applications", with_detail=True)),
	]


def build():
	return build_page(
		PAGE_NAME, ROUTE, "Documents", NAV_HREF, content(), data_script=DATA_SCRIPT
	)
