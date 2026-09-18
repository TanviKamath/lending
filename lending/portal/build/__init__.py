# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""One-shot generators for the borrower portal's Builder Pages.

Nothing here runs during a request. Each module builds one page once, with

	bench --site <site> execute lending.portal.build.<module>.build

after which the page is UI-owned: Builder exports every save to
lending/builder_files/, so the exported JSON -- not the module -- is the source of
truth, and re-running a build discards whatever was laid out on the canvas. Re-run
one only to rebuild a page from scratch, or after a shell or theme change that every
page has to pick up.

theme, shell and script are the ingredients rather than pages: the styles, the frame
every page shares, and the one client script it ships. They sit here because they are
read while a page is being built, not while one is being served.

The portal's live request code is the parent package; keeping the two apart is the
point of this one.
"""
