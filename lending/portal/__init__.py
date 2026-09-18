# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower portal: the pages a borrower signs in to, and the code behind them.

The modules beside this one answer requests. Every Builder page reaches them by name
through a data script -- `frappe.call("lending.portal.loans.get_loans_page")` -- because
a data script runs inside safe_exec and cannot import this package. Renaming one of
these modules therefore breaks a page silently, since the caller is a string in an
exported JSON rather than an import Python can check.

The pages themselves are not built here. `portal.build` holds the generators that laid
them out once; nothing in it runs while a request is being served.
"""
