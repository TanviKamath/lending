# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""One-shot generators for the borrower portal's Builder Pages.

Nothing here runs during a request. Each module builds one page once, with

	bench --site <site> execute lending.portal_build.<module>.build

after which the page is UI-owned: Builder exports every save to
lending/builder_files/, so the exported JSON -- not the module -- is the source of
truth, and re-running a build discards whatever was laid out on the canvas. Re-run
one only to rebuild a page from scratch, or after a portal_shell/portal_theme
change that every page has to pick up.

The portal's live request code is the sibling lending/portal*.py modules; keeping
the two apart is the point of this package.
"""
