# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint

# The data script every portal page runs reaches this app through one of these calls,
# so the scripts themselves say which Builder Pages belong to the portal. A hand-kept
# list of routes would have to be edited whenever a page is added, and the page that
# got missed would be the one still reachable with the portal switched off.
PORTAL_SCRIPT_MARKER = "lending.portal."

# The one page the public-apply switch governs on its own. Everything else, including
# the tracker, follows the portal switch.
APPLY_PAGE_MARKER = "lending.portal.apply.get_apply_page"

# Saving these is what restyles the portal. The rest of the Borrower Portal section is
# read per request, so only these need anything written when the form is saved.
STYLE_FIELDS = (
	"portal_brand_color",
	"portal_accent_color",
)


class LendingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_create_customer: DF.Check
		enable_borrower_portal: DF.Check
		enable_public_apply: DF.Check
		portal_accent_color: DF.Color | None
		portal_brand_color: DF.Color | None
		portal_brand_name: DF.Data | None
		portal_logo: DF.AttachImage | None
		portal_support_email: DF.Data | None
	# end: auto-generated types

	def on_update(self):
		sync_portal_pages()

		if any(self.has_value_changed(field) for field in STYLE_FIELDS):
			apply_brand_tokens()


def apply_brand_tokens():
	from lending.portal.build.theme import upsert_tokens

	upsert_tokens()


def sync_portal_pages():
	portal_on = cint(frappe.db.get_single_value("Lending Settings", "enable_borrower_portal"))
	apply_on = portal_on and cint(
		frappe.db.get_single_value("Lending Settings", "enable_public_apply")
	)

	pages = frappe.get_all(
		"Builder Page",
		filters={"page_data_script": ("like", f"%{PORTAL_SCRIPT_MARKER}%")},
		fields=["name", "route", "published", "page_data_script"],
	)

	changed = False
	for page in pages:
		wanted = apply_on if APPLY_PAGE_MARKER in (page.page_data_script or "") else portal_on
		if cint(page.published) == cint(wanted):
			continue

		# db_set rather than a save: in developer mode saving a Builder Page exports it
		# back over lending/builder_files/, so switching the portal off would rewrite the
		# app's own source.
		frappe.db.set_value("Builder Page", page.name, "published", cint(wanted))
		changed = True

	if changed:
		clear_portal_route_cache()


def clear_portal_route_cache():
	from builder.builder.doctype.builder_page.builder_page import (
		find_page_with_path,
		get_web_pages_with_dynamic_routes,
	)

	get_web_pages_with_dynamic_routes.clear_cache()
	find_page_with_path.clear_cache()
	frappe.clear_cache()
