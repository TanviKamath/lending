
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges. The application name is not passed from here: get_application_detail reads
# it from frappe.form_dict server-side and proves ownership before reading further.
data.update(frappe.call("lending.portal_applications.get_application_detail"))  # noqa: F821
