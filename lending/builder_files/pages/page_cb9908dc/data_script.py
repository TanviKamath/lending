
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: the product list and its copy arrive formatted from the data layer.
data.update(frappe.call("lending.portal.apply.get_apply_page"))  # noqa: F821
