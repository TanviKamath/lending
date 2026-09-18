# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint

# The data script every portal page runs reaches this app through one of these calls,
# so the scripts themselves say which Builder Pages belong to the portal. A hand-kept
# list of routes would have to be edited whenever a page is added, and the page that
# got missed would be the one still reachable with the portal switched off.
PORTAL_SCRIPT_MARKER = "lending.portal"

# The one page the public-apply switch governs on its own. Everything else, including
# the tracker, follows the portal switch.
APPLY_PAGE_MARKER = "lending.portal_apply.get_apply_page"

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
	"""Push the lender's colours into the Builder Tokens the pages read.

	The portal is styled through custom properties that Builder serves to the canvas
	and to the published page alike, so writing the tokens is what makes one desk form
	restyle every page at once. A colour left blank is not written, and the value the
	app ships with stands.
	"""
	from lending.portal_theme import upsert_tokens

	upsert_tokens()


def sync_portal_pages():
	"""Publish or unpublish the portal's Builder Pages to match the two switches.

	The data layer refuses on its own -- see lending.portal.assert_portal_enabled -- and
	that refusal is what protects the whitelisted endpoints, which have no route to take
	away. It is not enough for the pages themselves. A PageDoesNotExistError raised while
	a page renders comes back as the 404 page with a 200 status, because
	website/serve.py builds its NotFoundPage with the status code it was called with
	rather than with 404. Only a route that fails to resolve gives a real 404, and
	Builder resolves a route by looking for a published page.

	So the switch takes the page out of the route table. A lender who switched the portal
	off gets a portal that is absent, not one that answers every request with a cheerful
	200 and an apology.
	"""
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
	"""Drop the caches Builder reads a route through.

	Both are Builder's own, and both are keyed on published, so a page that has just been
	unpublished keeps resolving until they are cleared. Builder does this for itself in
	Builder Page.on_update, which db_set does not run.
	"""
	from builder.builder.doctype.builder_page.builder_page import (
		find_page_with_path,
		get_web_pages_with_dynamic_routes,
	)

	get_web_pages_with_dynamic_routes.clear_cache()
	find_page_with_path.clear_cache()
	frappe.clear_cache()
