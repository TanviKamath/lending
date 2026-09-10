
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges. The loan name is not passed from here: get_loan_detail reads it from
# frappe.form_dict server-side and proves the borrower owns it before reading further.
data.update(frappe.call("lending.portal_loans.get_loan_detail"))  # noqa: F821
