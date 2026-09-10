# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Personal details page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal_profile_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see portal_shell.
"""

from lending.portal_shell import build_page
from lending.portal_theme import card, note_panel, pair_rows

PAGE_NAME = "Borrower Profile"
ROUTE = "borrower/profile"
NAV_HREF = "/borrower/profile"
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal_profile.get_profile_page"))  # noqa: F821
'''


def content():
	return [
		card("Your details", "records_note", pair_rows("records", with_detail=True)),
		note_panel("edit_note"),
	]


def build():
	return build_page(
		PAGE_NAME, ROUTE, "Personal details", NAV_HREF, content(), data_script=DATA_SCRIPT
	)
