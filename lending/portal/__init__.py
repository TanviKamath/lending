# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower portal: the pages a borrower signs in to, and the code behind them.

The modules beside this one answer requests. Every page reaches them by name -- a Studio
API Resource whose url is `lending.portal.loans.get_loans_page` -- rather than by an
import, because the page is a definition in the database and the browser is what calls.
Renaming one of these modules therefore breaks a page silently, since the caller is a
string in an exported JSON rather than an import Python can check.

The pages themselves are not built here. `portal.studio_build` holds the generators that
laid them out; nothing in it runs while a request is being served.
"""
