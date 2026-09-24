# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint

# Which pages belong to the portal is the Studio App they sit under, so no list of
# routes is kept here: a page added to the app is governed by these switches from the
# moment it exists, and there is no page to forget.

# The one page the public-apply switch governs on its own. Everything else, including
# the tracker, follows the portal switch. Studio routes carry a leading slash.
APPLY_ROUTE = "/apply"


class LendingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from lending.loan_management.doctype.portal_footer_link.portal_footer_link import (
			PortalFooterLink,
		)

		auto_create_customer: DF.Check
		enable_borrower_portal: DF.Check
		enable_public_apply: DF.Check
		portal_brand_name: DF.Data | None
		portal_copyright: DF.Data | None
		portal_footer_links: DF.Table[PortalFooterLink]
		portal_logo: DF.AttachImage | None
		portal_primary_color: DF.Color | None
		portal_secondary_color: DF.Color | None
		portal_support_email: DF.Data | None
	# end: auto-generated types

	def on_update(self):
		sync_portal_pages()


def sync_portal_pages():
	"""Publish or unpublish the portal's pages to match the two switches.

	A Studio App is served only while it has a published page, so unpublishing every
	page is what takes the portal off the website: the route stops resolving rather
	than answering with a page that says it is closed.
	"""
	portal_on = cint(frappe.db.get_single_value("Lending Settings", "enable_borrower_portal"))
	apply_on = portal_on and cint(
		frappe.db.get_single_value("Lending Settings", "enable_public_apply")
	)

	pages = frappe.get_all(
		"Studio Page",
		filters={"studio_app": portal_app()},
		fields=["name", "route", "published"],
	)

	changed = False
	for page in pages:
		wanted = apply_on if page.route == APPLY_ROUTE else portal_on
		if cint(page.published) == cint(wanted):
			continue

		# db_set rather than a save: in developer mode saving a Studio Page exports it
		# back over lending/studio/, so switching the portal off would rewrite the app's
		# own source.
		frappe.db.set_value("Studio Page", page.name, "published", cint(wanted))
		frappe.clear_document_cache("Studio Page", page.name)
		changed = True

	if changed:
		frappe.clear_cache()


def portal_app() -> str:
	"""The Studio App the portal's pages belong to.

	Imported rather than spelt again: the generator names the app, and a second copy of
	that string here would leave the switches quietly governing nothing the day it was
	renamed. The import is inside the function because the package it lives in pulls in
	every page module, and this runs on a save rather than on a request.
	"""
	from lending.portal.studio_build.app import APP_NAME

	return APP_NAME
