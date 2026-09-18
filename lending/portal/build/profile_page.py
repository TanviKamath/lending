# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Personal details page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.profile_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.

The page reads first and edits second. Everything on record is listed, and one Edit
button opens the form that corrects the parts section 6.3 of PORTAL_PLAN.md allows --
contact details and address. Name and tax id appear in the list and in no input,
because they are the outcome of a KYC check rather than a preference.

The form stays hidden until that button is pressed. A borrower opening this page has
come to check what is on record far more often than to change it, and a page that
opens with nine empty boxes below the answer asks to be filled in.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import (
	BTN_STYLES,
	CARD_HEAD_STYLES,
	CARD_STYLES,
	CARD_SUB_STYLES,
	CARD_TITLE_STYLES,
	ERROR_STYLES,
	FIELD_GRID_STYLES,
	FIELD_GRID_TABLET_STYLES,
	GHOST_BTN_STYLES,
	SUBMIT_ROW_STYLES,
	block,
	bound,
	bound_field,
	card,
	hidden_field,
	note_panel,
	offer_card,
	pair_rows,
	reveal_button,
	switch_links,
)

# What the Edit button opens. The button and the form are built apart, so they agree
# on one name rather than on where they sit.
EDIT_PANEL = "profile-edit"

PAGE_NAME = "Borrower Profile"
ROUTE = "borrower/profile"
NAV_HREF = "/borrower/profile"
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal.profile.get_profile_page"))  # noqa: F821
'''


def edit_form():
	"""One form, aimed at one customer record, posting a fixed list of fields."""
	return block(
		"form",
		styles=CARD_STYLES,
		attributes={
			"data-endpoint": "lending.portal.profile.save_profile",
			# The list above the form is now stale, so the page re-reads itself.
			"data-reload": "1",
			"data-revealed": EDIT_PANEL,
			"hidden": "hidden",
		},
		children=[
			block(
				"div",
				styles=CARD_HEAD_STYLES,
				children=[
					block("h2", styles=CARD_TITLE_STYLES, html="Edit your details"),
					bound("div", "form_note", styles=CARD_SUB_STYLES),
				],
			),
			switch_links("customer_options"),
			hidden_field("customer", "form_customer"),
			block(
				"div",
				styles=FIELD_GRID_STYLES,
				tabletStyles=FIELD_GRID_TABLET_STYLES,
				children=[
					bound_field("Email", "email", "form_email", input_type="email"),
					bound_field("Mobile", "mobile", "form_mobile", input_type="tel"),
					bound_field("Phone", "phone", "form_phone", input_type="tel"),
					bound_field("Address line 1", "address_line1", "form_address_line1"),
					bound_field("Address line 2", "address_line2", "form_address_line2"),
					bound_field("City", "city", "form_city"),
					bound_field("State", "state", "form_state"),
					bound_field("Pin code", "pincode", "form_pincode"),
					bound_field("Country", "country", "form_country"),
				],
			),
			block(
				"div",
				styles=SUBMIT_ROW_STYLES,
				children=[
					block(
						"button",
						styles=BTN_STYLES,
						children=[bound("span", "save_label")],
						attributes={"type": "button", "data-submit": "1"},
					),
					block(
						"button",
						styles=GHOST_BTN_STYLES,
						html="Cancel",
						attributes={"type": "button", "data-hides": EDIT_PANEL},
					),
				],
			),
			block(
				"div",
				styles={**ERROR_STYLES, "margin": "0 12px 12px"},
				attributes={"data-error": "1", "hidden": "hidden"},
			),
			block("div", styles={"padding": "0 12px 12px"}, children=[offer_card(action_href="#")]),
		],
	)


def content():
	return [
		card(
			"On record",
			"records_note",
			pair_rows("records", with_detail=True),
			action=reveal_button("Edit", EDIT_PANEL),
		),
		note_panel("edit_note"),
		edit_form(),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Personal details",
		NAV_HREF,
		content(),
		data_script=DATA_SCRIPT,
	)
