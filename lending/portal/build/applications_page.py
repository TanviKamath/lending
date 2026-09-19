# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Applications list as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.applications_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import (
	AMOUNT_STYLES,
	PRIMARY_TEXT_STYLES,
	SECONDARY_TEXT_STYLES,
	STATE_STYLES,
	WHY_STYLES,
	bound,
	card,
	pair_rows,
	record_table,
)

PAGE_NAME = "Borrower Applications"
ROUTE = "borrower/applications"
ACTION_HREF = "/apply"

DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal.applications.get_applications_page"))  # noqa: F821
'''


def applications_body():
	"""Each row links to its own tracker, so the whole line is the way in."""
	why = bound("div", "note", styles=WHY_STYLES)
	why["visibilityCondition"] = "note"

	return record_table(
		["Application", "Stage", "Amount sought"],
		[
			[
				bound("div", "product", styles=PRIMARY_TEXT_STYLES),
				bound("div", "reference", styles=SECONDARY_TEXT_STYLES),
				why,
			],
			[bound("span", "stage", styles=STATE_STYLES)],
			[bound("div", "amount", styles=AMOUNT_STYLES)],
		],
		"applications",
	)


def content():
	return [
		card("Applications", "applications_note", applications_body()),
		# What a borrower has before any of it becomes an application. On the day they
		# sign up this card is their whole account, so the page cannot leave it out.
		card("Enquiries", "enquiries_note", pair_rows("enquiries", with_detail=True)),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Applications",
		content(),
		action_href=ACTION_HREF,
		data_script=DATA_SCRIPT,
	)
