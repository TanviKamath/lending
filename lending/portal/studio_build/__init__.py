# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower portal, built again as a Frappe Studio app.

Run the whole thing once with

	bench --site <site> execute lending.portal.studio_build.build

and then, so the app has a bundle to serve rather than only a definition,

	bench --site <site> execute lending.portal.studio_build.bundle

after which the portal answers at /borrower-portal/overview. Until the bundle exists the
route falls back to Studio's own renderer, which serves the pages from the editor's
assets -- fine for a look, not for a borrower.

What this package is
--------------------
The portal was first built on Frappe Builder. This package lays the same portal out as
Studio pages, against the same endpoints -- `lending.portal.*`, unchanged -- so the
move was a re-layout rather than a rewrite: what changed is the thing that draws the
payload, not the thing that produces it.

The Builder portal is not on this branch. It lives on feature/borrower-portal, where it
still answers on /borrower/*, /apply and /track; here there is one portal, and it is
this one.

What moved, and what it became
------------------------------
	Builder                                Studio
	a styled span with a data-tone         a frappe-ui Badge
	a grid of divs with column widths      the List family
	an <input> and a client script         FormControl over a page-script ref
	a hand-built tab strip                 TabButtons and a ref
	seven panels and a display toggle      a `step` ref and visibility conditions
	one component wrapped round a page     three components beside the content
	a Python data script in safe_exec      an API Resource on the same endpoint
	the shared client script               each page's setup() module

The one thing that did not survive the move is the portal's own design system: some
thirty CSS custom properties driven by Lending Settings, and the inline styles on every
block. The Studio pages take frappe-ui's own appearance instead, which is the point of
asking for components rather than divs -- what is on the canvas now is a component to
restyle rather than a div already painted. Brand colour, logo, radius and font are
therefore not yet wired in.

Where the work is
-----------------
`blocks` is the vocabulary, `app` creates the documents, `shell` is the frame, and one
module per page after that. Studio's own exporters write everything to
lending/studio/borrower_portal/ as it is saved.
"""

from lending.portal.studio_build import (
	app,
	application_pages,
	apply_page,
	documents_page,
	loan_pages,
	overview_page,
	profile_page,
	search_page,
	shell,
	statement_pages,
	track_page,
)


def build():
	"""Create or replace the whole app: the frame first, then every page.

	Safe to re-run, and it has to be re-run as a whole: the pages share the frame's
	components, so a change to one of those reaches a page only when its own blocks
	are rebuilt around it.

	It is not, however, meant to be run twice. Once a page has been opened in Studio and
	saved, the canvas owns it: Studio exports every save to lending/studio/borrower_portal/,
	so the exported JSON is the source of truth from that point and re-running this
	would discard whatever was laid out there.
	"""
	app.upsert_app()
	shell.upsert_frame()

	pages = [
		overview_page.build(),
		*loan_pages.build(),
		*application_pages.build(),
		documents_page.build(),
		*statement_pages.build(),
		profile_page.build(),
		search_page.build(),
		apply_page.build(),
		track_page.build(),
	]

	print(f"built {len(pages)} Studio pages under /{app.APP_NAME}")

	return pages


def bundle():
	"""Build the app's frontend bundle, which is what the published route serves.

	Studio rebuilds this itself on migrate for its own apps; an app exported into
	another Frappe app is built when somebody asks, so this is the asking.
	"""
	import frappe

	result = frappe.get_doc("Studio App", app.APP_NAME).generate_app_build()
	if error := result.get("build_error"):
		print(f"build failed -- see Error Log {error.get('error_log')}")
	else:
		print(f"built the bundle for {app.APP_NAME}")

	return result
