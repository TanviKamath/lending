
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer,
# reached through the whitelisted door the Loan Lead server scripts use.
data.update(frappe.call("lending.portal.core.get_dashboard"))  # noqa: F821
