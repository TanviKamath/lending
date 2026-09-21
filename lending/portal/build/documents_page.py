# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower's Documents page as a standard Builder page.

Run once with:
	bench --site <site> execute lending.portal.build.documents_page.build

Then stop running it. The page becomes UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas. The frame comes from the shell component; see shell.

The upload form only appears when there is a draft application to attach to. A
submitted application is with our team, and section 6.2 of PORTAL_PLAN.md keeps the
borrower out of it from that point, so offering a file picker that the server would
refuse would be a worse page than offering none.

The applications at the foot are the reason to come back: each says which step of its
tracker it is standing on and how many files it already holds, and opens the tracker
itself.
"""

from lending.portal.build.shell import build_page
from lending.portal.build.theme import (
	AMOUNT_STYLES,
	BTN_STYLES,
	CARD_HEAD_STYLES,
	CARD_STYLES,
	CARD_SUB_STYLES,
	CARD_TITLE_STYLES,
	ERROR_STYLES,
	FIELD_GRID_STYLES,
	FIELD_GRID_TABLET_STYLES,
	PRIMARY_TEXT_STYLES,
	SECONDARY_TEXT_STYLES,
	SUBMIT_ROW_STYLES,
	badge,
	block,
	bound,
	card,
	file_field,
	note_panel,
	offer_card,
	pair_rows,
	record_table,
	select_field,
)

PAGE_NAME = "Borrower Documents"
ROUTE = "borrower/documents"
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal.applications.get_documents_page"))  # noqa: F821
data.update(frappe.call("lending.portal.applications.get_document_choices"))  # noqa: F821
'''


def upload_form():
	node = block(
		"form",
		styles=CARD_STYLES,
		attributes={
			"data-endpoint": "lending.portal.applications.upload_document",
			# A file input only reaches the server in a multipart body.
			"data-upload": "1",
			"data-reload": "1",
		},
		children=[
			block(
				"div",
				styles=CARD_HEAD_STYLES,
				children=[
					block("h2", styles=CARD_TITLE_STYLES, html="Send us a document"),
					bound("div", "upload_note", styles=CARD_SUB_STYLES),
				],
			),
			block(
				"div",
				styles=FIELD_GRID_STYLES,
				tabletStyles=FIELD_GRID_TABLET_STYLES,
				children=[
					select_field("For which application", "application", "application_options"),
					select_field("What is it", "document_type", "document_type_options"),
				],
			),
			file_field(
				"Choose the file",
				"file",
				".pdf,.png,.jpg,.jpeg",
				note="A PDF or a photo, up to 5 MB. We keep it private.",
			),
			block(
				"div",
				styles=SUBMIT_ROW_STYLES,
				children=[
					block(
						"button",
						styles=BTN_STYLES,
						children=[bound("span", "upload_label")],
						attributes={"type": "button", "data-submit": "1"},
					)
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
	# Hidden unless the borrower has a draft application to attach to.
	node["visibilityCondition"] = "can_upload"

	return node


def no_upload_note():
	"""Shown instead of the form. note_panel hides on an empty value, and this value
	is never empty, so the condition has to be the opposite of the form's."""
	node = note_panel("no_upload_note")
	node["visibilityCondition"] = "not can_upload"

	return node


def applications_body():
	"""Each application, where it has reached, and how much of it is already here.

	The same rows appear on the Applications page against the amount sought. Here the
	last column counts files instead: on this page the question is which application
	is still waiting for something to be sent.
	"""
	return record_table(
		["Application", "Stage", "Documents"],
		[
			[
				bound("div", "product", styles=PRIMARY_TEXT_STYLES),
				bound("div", "reference", styles=SECONDARY_TEXT_STYLES),
				bound("div", "progress", styles=SECONDARY_TEXT_STYLES),
			],
			[badge("stage", tone_key="stage_tone")],
			[bound("div", "attached", styles=AMOUNT_STYLES)],
		],
		"applications",
	)


def content():
	return [
		card("Documents you have sent", "documents_note", pair_rows("documents", with_detail=True, marker=True)),
		upload_form(),
		no_upload_note(),
		card("Applications", "applications_note", applications_body()),
	]


def build():
	return build_page(
		PAGE_NAME,
		ROUTE,
		"Documents",
		content(),
		data_script=DATA_SCRIPT,
	)
